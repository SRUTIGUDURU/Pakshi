"""
Pakshi — Intent Parser (Ultra-Comprehensive – handles dialects, misspellings, STT audio errors)
Upgraded with Word-Boundary Enforcement, Negation Shielding, and Phonetic Collapsing.
"""
import re
import json
import difflib
from pathlib import Path
from dataclasses import dataclass, field, asdict

@dataclass
class IntentResult:
    feel:          list[str]       = field(default_factory=list)
    occasion:      str | None      = None
    budget:        int | None      = None
    budget_flex:   bool            = False
    color:         str | None      = None
    color_family:  str | None      = None
    location:      str | None      = None
    weave:         list[str]       = field(default_factory=list)
    fabric:        list[str]       = field(default_factory=list)
    urgency_days:  int | None      = None
    language_hint: str             = "english"
    raw_input:     str             = ""
    confidence:    float           = 0.0
    missing:       list[str]       = field(default_factory=list)
    warnings:      list[str]       = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

BASE_DIR = Path(__file__).parent
_ONTOLOGY = {"fabrics": []}
try:
    with open(BASE_DIR / "fabric_ontology.json", encoding="utf-8") as _f:
        _ONTOLOGY = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    pass

_VALID_SENSORY = set()
for _fab in _ONTOLOGY.get("fabrics", []):
    _VALID_SENSORY.update(_fab.get("sensory_descriptors", []))

# ---------- NORMALISATION (Phonetic collapsing + STT audio fixes) ----------
def _normalise_text(text: str) -> str:
    """Apply Indic phonetic vowel collapsing, STT boundary fixes, and typo repairs."""
    if not text:
        return ""
    
    # 1. Phonetic vowel/consonant collapsing for Romanized Indic STT errors
    # Collapses repeating vowels (e.g., Kancheepuram -> Kanchipuram, ikaat -> ikat)
    text = re.sub(r'([a-z])\1+', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'ee+', 'i', text, flags=re.IGNORECASE)
    text = re.sub(r'oo+', 'u', text, flags=re.IGNORECASE)
    
    # 2. Structural punctuation and hyphen normalization
    text = text.replace("-", " ").replace("_", " ")
    
    # 3. Explicit high-priority replacements
    replacements = {
        # Weave fixes
        "टिकट": "इकट", "tikat": "ikat", "ikhat": "ikat", "icat": "ikat", "ikaat": "ikat", "इकाट": "इकट",
        # Budget fixes
        "आईएस": "आरएस", "आइएस": "आरएस", "rs.": "rs", "r.s.": "rs", "r s": "rs", "rupees": "rs", "rupee": "rs",
        # Location fixes
        "बनारसी": "बनारस", "वाराणसी": "Varanasi", "बनारस": "Varanasi", "banaras": "Varanasi", "kancheepuram": "Kanchipuram",
        # Occasion fixes
        "वेडिंग": "शादी", "वेडींग": "शादी",
        # Color fixes
        "ब्लू": "नीला", "ग्रीन": "हरा", "येलो": "पीला", "रेड": "लाल", "ब्लैक": "काला", "पिंक": "गुलाबी",
        # Feel fixes
        "लाइट": "हल्का", "हैवी": "भारी", "सॉफ्ट": "नरम", "रिच": "शानदार", "रॉयल": "शाही", "फ्लोई": "बहने वाला", "ब्रीदेबल": "सांस लेने योग्य",
        # Fabric fixes
        "सिल्क": "रेशम", "कॉटन": "सूती", "सूत": "सूती", "रेशमी": "रेशम"
    }
    
    for target, replacement in replacements.items():
        # Case-insensitive replacement for Roman script; direct for Devanagari
        text = re.sub(rf'(?<!\w){re.escape(target)}(?!\w)', replacement, text, flags=re.IGNORECASE)
        
    return re.sub(r'\s+', ' ', text).strip()

# ---------- OCCASION ALIASES (ultra-expanded) ----------
OCCASION_ALIASES = {
    "wedding": "wedding", "shaadi": "wedding", "shadi": "wedding", "marriage": "wedding",
    "nikah": "wedding", "vivah": "wedding", "kalyanam": "wedding", "pelli": "wedding",
    "reception": "reception", "engagement": "reception", "roka": "reception", "mangni": "reception",
    "festival": "festival", "puja": "festival", "pooja": "festival", "navratri": "festival",
    "dussehra": "festival", "diwali": "festival", "deepavali": "festival", "onam": "festival",
    "pongal": "festival", "ugadi": "festival", "sankranti": "festival", "eid": "festival",
    "durga puja": "festival", "holi": "festival", "dasara": "festival", "teej": "festival",
    "casual": "casual", "daily": "daily_wear", "daily wear": "daily_wear", "everyday": "daily_wear",
    "regular": "daily_wear", "roz ka": "daily_wear", "office": "work", "work": "work",
    "professional": "work", "formal": "formal", "semi formal": "semi_formal", "party": "semi_formal",
    "ceremony": "ceremony", "gruhapravesam": "ceremony", "housewarming": "ceremony", "college": "college",
    "university": "college", "campus": "college", "शादी": "wedding", "विवाह": "wedding",
    "निकाह": "wedding", "रिसेप्शन": "reception", "सगाई": "reception", "मंगनी": "reception",
    "त्योहार": "festival", "पूजा": "festival", "दिवाली": "festival", "होली": "festival",
    "ऑफिस": "work", "कार्यालय": "work", "कॉलेज": "college", "समारोह": "ceremony",
    "रोज़": "daily_wear", "कैज़ुअल": "casual", "फेस्टिवल": "festival", "फेस्टीवल": "festival",
}

# ---------- FEEL KEYWORDS (ultra-expanded) ----------
FEEL_KEYWORDS = {
    "light": ["light", "airy"], "halka": ["light", "airy"], "lightweight": ["light", "airy"],
    "heavy": ["heavy", "stiff"], "bhaari": ["heavy", "stiff"], "grand": ["heavy", "royal"],
    "soft": ["soft", "comfortable"], "naram": ["soft"], "mulmul": ["soft", "airy"],
    "rich": ["rich", "elegant"], "royal": ["royal", "grand"], "shahi": ["royal", "grand"],
    "luxurious": ["luxurious", "rich"], "flowy": ["flowy", "airy"], "drapey": ["flowy", "soft"],
    "breathable": ["breathable", "airy"], "cool": ["cool", "breathable"], "glossy": ["glossy"],
    "shiny": ["glossy", "rich"], "stiff": ["stiff"], "crisp": ["stiff"], "comfortable": ["comfortable"],
    "traditional": ["traditional"], "elegant": ["elegant"], "classy": ["elegant", "rich"],
    "silk": ["rich", "elegant"], "रेशम": ["rich", "elegant"], "हल्का": ["light", "airy"],
    "भारी": ["heavy", "stiff"], "नरम": ["soft"], "शाही": ["royal", "grand"],
    "शानदार": ["luxurious", "rich"], "बहने वाला": ["flowy", "airy"], "सांस लेने योग्य": ["breathable", "airy"],
    "ठंडा": ["cool", "breathable"], "चमकदार": ["glossy", "shiny"], "कड़ा": ["stiff"],
    "आरामदायक": ["comfortable"], "पारंपरिक": ["traditional"], "लाइट": ["light", "airy"],
    "फ्लोई": ["flowy", "airy"], "हैवी": ["heavy", "stiff"], "सॉफ्ट": ["soft", "comfortable"],
    "रिच": ["rich", "elegant"], "रॉयल": ["royal", "grand"],
}

# ---------- COLOR KEYWORDS (ultra-expanded) ----------
COLOR_KEYWORDS = {
    "red": ("red", "red"), "pink": ("pink", "pink"), "blue": ("blue", "blue"),
    "green": ("green", "green"), "yellow": ("yellow", "yellow"), "orange": ("orange", "orange"),
    "purple": ("purple", "purple"), "white": ("white", "neutral"), "black": ("black", "neutral"),
    "beige": ("beige", "neutral"), "grey": ("grey", "neutral"), "gray": ("grey", "neutral"),
    "maroon": ("maroon", "red"), "navy": ("navy blue", "blue"), "teal": ("teal", "green"),
    "mint": ("mint green", "green"), "lavender": ("lavender", "purple"), "lilac": ("lilac", "purple"),
    "coral": ("coral", "pink"), "peach": ("peach", "orange"), "rust": ("rust", "orange"),
    "terracotta": ("rust", "orange"), "saffron": ("saffron", "orange"), "gold": ("soft gold", "yellow"),
    "golden": ("soft gold", "yellow"), "champagne": ("champagne", "yellow"), "ivory": ("ivory", "neutral"),
    "cream": ("cream", "neutral"), "brown": ("brown", "neutral"), "magenta": ("magenta", "pink"),
    "mustard": ("mustard", "yellow"), "turquoise": ("turquoise", "blue"), "olive": ("olive", "green"),
    "लाल": ("red", "red"), "गुलाबी": ("pink", "pink"), "नीला": ("blue", "blue"),
    "नीली": ("blue", "blue"), "नीले": ("blue", "blue"), "हरा": ("green", "green"),
    "हरी": ("green", "green"), "हरे": ("green", "green"), "पीला": ("yellow", "yellow"),
    "पीली": ("yellow", "yellow"), "पीले": ("yellow", "yellow"), "नारंगी": ("orange", "orange"),
    "संतरी": ("orange", "orange"), "बैंगनी": ("purple", "purple"), "जामुनी": ("purple", "purple"),
    "सफेद": ("white", "neutral"), "सफ़ेद": ("white", "neutral"), "काला": ("black", "neutral"),
    "काली": ("black", "neutral"), "काले": ("black", "neutral"), "भूरा": ("brown", "neutral"),
    "भूरी": ("brown", "neutral"), "ग्रे": ("grey", "neutral"), "धूसर": ("grey", "neutral"),
    "ब्लू": ("blue", "blue"), "ग्रीन": ("green", "green"), "येलो": ("yellow", "yellow"),
    "रेड": ("red", "red"), "ब्लैक": ("black", "neutral"), "पिंक": ("pink", "pink"),
    "ऑरेंज": ("orange", "orange"),
}

# ---------- LOCATION ALIASES (ultra-expanded & safely bounded) ----------
LOCATION_ALIASES = {
    "Varanasi": "Varanasi", "banaras": "Varanasi", "varanasi": "Varanasi", "kashi": "Varanasi",
    "बनारस": "Varanasi", "वाराणसी": "Varanasi", "बनारसी": "Varanasi", "काशी": "Varanasi",
    "Kanchipuram": "Kanchipuram", "kanchipuram": "Kanchipuram", "kancheepuram": "Kanchipuram",
    "kanjivaram": "Kanchipuram", "kanchi": "Kanchipuram", "कांचीपुरम": "Kanchipuram", "कांची": "Kanchipuram",
    "Venkatagiri": "Venkatagiri", "venkatagiri": "Venkatagiri", "venkata giri": "Venkatagiri",
    "वेंकटागिरी": "Venkatagiri", "वेंकटगिरी": "Venkatagiri",
    "Pochampally": "Pochampally", "pochampally": "Pochampally", "pochampalli": "Pochampally",
    "पोचमपल्ली": "Pochampally", "पोचम्पल्ली": "Pochampally",
    "Ilkal": "Ilkal", "ilkal": "Ilkal", "इलकल": "Ilkal",
    "Kota": "Kota", "kota": "Kota", "कोटा": "Kota",
    "Chanderi": "Chanderi", "chanderi": "Chanderi", "चंदेरी": "Chanderi",
    "Maheshwar": "Maheshwar", "maheshwar": "Maheshwar", "maheshwari": "Maheshwar",
    "महेश्वर": "Maheshwar", "महेश्वरी": "Maheshwar",
    "Dharmavaram": "Dharmavaram", "dharmavaram": "Dharmavaram", "धर्मावरम": "Dharmavaram",
    "Mysore": "Mysore", "mysore": "Mysore", "मैसूर": "Mysore",
    "Sambalpuri": "Sambalpuri", "sambalpuri": "Sambalpuri", "sambalpur": "Sambalpuri",
    "संबलपुर": "Sambalpuri", "संबलपुरी": "Sambalpuri",
    "Bagru": "Bagru", "bagru": "Bagru", "बागरू": "Bagru",
    "Sanganer": "Sanganer", "sanganer": "Sanganer", "संगानेर": "Sanganer",
    "Kutch": "Kutch", "kutch": "Kutch", "कच्छ": "Kutch",
    "Kerala": "Kerala", "kerala": "Kerala", "केरल": "Kerala",
    "Tamil Nadu": "Tamil Nadu", "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu",
    "तमिलनाडु": "Tamil Nadu", "तमिल": "Tamil Nadu",
    "Andhra Pradesh": "Andhra Pradesh", "andhra pradesh": "Andhra Pradesh", "andhra": "Andhra Pradesh",
    "आंध्र": "Andhra Pradesh", "आंध्र प्रदेश": "Andhra Pradesh",
    "Telangana": "Telangana", "telangana": "Telangana", "तेलंगाना": "Telangana",
    "Karnataka": "Karnataka", "karnataka": "Karnataka", "कर्नाटक": "Karnataka",
    "Rajasthan": "Rajasthan", "rajasthan": "Rajasthan", "राजस्थान": "Rajasthan",
    "West Bengal": "West Bengal", "west bengal": "West Bengal", "westbengal": "West Bengal",
    "bengal": "West Bengal", "पश्चिम बंगाल": "West Bengal", "बंगाल": "West Bengal",
    "Odisha": "Odisha", "odisha": "Odisha", "orissa": "Odisha", "उड़ीसा": "Odisha", "ओडिशा": "Odisha",
    "Gujarat": "Gujarat", "gujarat": "Gujarat", "गुजरात": "Gujarat",
    "Maharashtra": "Maharashtra", "maharashtra": "Maharashtra", "महाराष्ट्र": "Maharashtra",
    "Bihar": "Bihar", "bihar": "Bihar", "बिहार": "Bihar",
    "Uttar Pradesh": "Uttar Pradesh", "uttar pradesh": "Uttar Pradesh", "u.p.": "Uttar Pradesh",
    "उत्तर प्रदेश": "Uttar Pradesh",
}

# ---------- WEAVE / STYLE ALIASES (ultra-expanded) ----------
WEAVE_ALIASES = {
    "ikat": "ikat", "ikhat": "ikat", "icat": "ikat", "ikaat": "ikat", "pochampally": "ikat",
    "patola": "patola", "इकट": "ikat", "टिकट": "ikat", "इकाट": "ikat", "ईकट": "ikat", "पटोला": "patola",
    "block print": "block print", "blockprint": "block print", "block-print": "block print",
    "bagru": "block print", "sanganeri": "block print", "kalamkari": "kalamkari",
    "블ॉक प्रिंट": "block print", "ब्लाक प्रिंट": "block print", "कलमकारी": "kalamkari",
    "jamdani": "jamdani", "jhamdani": "jamdani", "dhaakai": "jamdani", "dhakai": "jamdani", "जामदानी": "jamdani",
    "kanjivaram": "kanjivaram", "kanchipuram": "kanjivaram", "pattu": "kanjivaram",
    "कांचीपुरम": "kanjivaram", "कांची": "kanjivaram", "पट्टू": "kanjivaram",
    "tussar": "tussar", "tusar": "tussar", "bhagalpuri": "tussar", "kosa": "tussar",
    "तुस्सर": "tussar", "तुसर": "tussar", "कोसा": "tussar",
    "banarasi": "banarasi", "banarsi": "banarasi", "brocade": "brocade", "brokade": "brocade",
    "tanchoi": "banarasi", "kinkhab": "brocade", "बनारसी": "banarasi", "ब्रोकेड": "brocade",
    "paithani": "paithani", "पैठणी": "paithani", "पैठनी": "paithani",
    "kota doria": "kota doria", "kotadoria": "kota doria", "kota": "kota doria", "कोटा डोरिया": "kota doria",
    "chanderi": "chanderi", "chandheri": "chanderi", "चंदेरी": "chanderi",
    "maheshwari": "maheshwari", "maheshwar": "maheshwari", "महेश्वरी": "maheshwari",
    "sambalpuri": "sambalpuri", "sambhalpuri": "sambalpuri", "bomkai": "sambalpuri", "संबलपुरी": "sambalpuri",
    "ilkal": "ilkal", "इलकल": "ilkal",
    "venkatagiri": "venkatagiri", "वेंकटागिरी": "venkatagiri",
    "zari": "zari", "zariwork": "zari", "zardozi": "zari", "gotta patti": "zari", "जरी": "zari",
    "kasavu": "kasavu", "settu mundu": "kasavu", "kerala saree": "kasavu", "कसावु": "kasavu",
    "temple border": "temple border", "templeborder": "temple border", "korvai": "temple border", "मंदिर बॉर्डर": "temple border",
    "handloom": "handloom", "handwoven": "handloom", "khadi": "handloom", "हथकरघा": "handloom", "खादी": "handloom",
    "bandhani": "bandhani", "bandhej": "bandhani", "tie dye": "bandhani", "बांधनी": "bandhani", "बंधेज": "bandhani",
    "leheriya": "leheriya", "लहरिया": "leheriya",
    "chikankari": "chikankari", "lakhnavi": "chikankari", "चिकनकारी": "chikankari", "लखनवी": "chikankari",
}

# ---------- FABRIC TYPE ALIASES (ultra-expanded & strictly bounded) ----------
FABRIC_ALIASES = {
    "cotton": "cotton", "suti": "cotton", "mulmul": "cotton", "khadi": "cotton",
    "कॉटन": "cotton", "सूती": "cotton", "सूत": "cotton", "मलमल": "cotton",
    "silk": "silk", "resham": "silk", "pattu": "silk", "raw silk": "silk",
    "सिल्क": "silk", "रेशम": "silk", "रेशमी": "silk", "पट्टू": "silk",
    "cotton silk": "cotton_silk", "cotton-silk": "cotton_silk", "chanderi silk": "cotton_silk",
    "sico": "cotton_silk", "maheshwari silk": "cotton_silk", "tussar silk": "silk",
    "कॉटन सिल्क": "cotton_silk", "सूती रेशम": "cotton_silk",
    "tussar": "silk", "bhagalpuri": "silk", "banarasi silk": "silk", "kanjivaram silk": "silk",
    "linen": "linen", "लिनन": "linen",
    "wool": "wool", "pashmina": "wool", "ऊन": "wool", "पश्मीना": "wool",
    "polyester": "synthetic", "chiffon": "synthetic", "georgette": "synthetic",
    "crepe": "synthetic", "organza": "synthetic", "net": "synthetic", "satin": "synthetic",
    "rayon": "synthetic", "viscose": "synthetic", "art silk": "synthetic",
    "पॉलिएस्टर": "synthetic", "शिफॉन": "synthetic", "जॉर्जेट": "synthetic", "क्रेप": "synthetic", "ऑर्गेंजा": "synthetic",
}

# ---------- BUDGET (handles all Indian numeral formatting & abbreviations) ----------
_DEVANAGARI_DIGITS = { '०':'0','१':'1','२':'2','३':'3','४':'4', '५':'5','६':'6','७':'7','८':'8','९':'9' }
def _devanagari_to_arabic(s: str) -> str:
    return ''.join(_DEVANAGARI_DIGITS.get(c, c) for c in s)

def _parse_budget(text: str):
    text_num = _devanagari_to_arabic(text).lower().replace(",", "")
    
    # Detect flexibility words
    flex = bool(re.search(
        r"\b(around|approx|approximately|under|below|less than|se kam|tak|max|maximum|budget|range|लगभग|करीब|तक|से कम|अंडर|बेलो)\b", 
        text_num, re.IGNORECASE
    ))
    
    # 1. Thousands multiplier patterns (e.g., "5k", "rs 10 k", "12.5k")
    k_match = re.search(r"(?:₹|rs\.?|inr|रु\.?|रुपये?|आरएस|rs)?\s*(\d+(?:\.\d+)?)\s*k\b", text_num, re.IGNORECASE)
    if k_match:
        try:
            val = int(float(k_match.group(1)) * 1000)
            if 100 <= val <= 500000: return val, flex
        except ValueError: pass

    # 2. Explicit currency symbols or words preceding/succeeding numbers
    curr_patterns = [
        r"(?:₹|rs\.?|inr|रु\.?|रुपये?|रु|आरएस|rs)\s*(\d{3,6})\b",
        r"\b(\d{3,6})\s*(?:rupees?|rs\.?|inr|रुपये?|रु|आरएस|rs|-|ka|ki|ke|wale|wali| budget)\b"
    ]
    for pat in curr_patterns:
        m = re.search(pat, text_num, re.IGNORECASE)
        if m:
            try:
                val = int(m.group(1))
                if 200 <= val <= 500000: return val, flex
            except ValueError: pass

    # 3. Fallback: Standalone 3 to 5 digit numbers if context implies price
    if any(w in text_num for w in ["price", "cost", "range", "budget", "rate", "dam", "daam", "कीमत", "दाम", "बजट"]):
        m = re.search(r"\b(\d{3,5})\b", text_num)
        if m:
            try:
                val = int(m.group(1))
                if 300 <= val <= 200000: return val, flex
            except ValueError: pass

    return None, False

# ---------- URGENCY (ultra-expanded) ----------
URGENCY_PATTERNS = [
    (re.compile(r"\b(?:today|abhi|aaj|right now|immediately|asap|urgent|turant|आज|अभी|आज ही|तुरंत|जरूरी)\b", re.I), 1),
    (re.compile(r"\b(?:tomorrow|tomor|kal|कल|आने वाला कल)\b", re.I), 2),
    (re.compile(r"\b(?:2\s*days?|do\s*din|within 48 hours|दो दिन|2 दिन)\b", re.I), 2),
    (re.compile(r"\b(?:3\s*days?|teen\s*din|तीन दिन|3 दिन)\b", re.I), 3),
    (re.compile(r"\b(?:4\s*days?|chaar\s*din|चार दिन|4 दिन)\b", re.I), 4),
    (re.compile(r"\b(?:this\s*week|is\s*hafte|5\s*days?|paanch\s*din|इस हफ्ते|इस सप्ताह|5 दिन)\b", re.I), 5),
    (re.compile(r"\b(?:week|hafte|saptah|7\s*days?|saat\s*din|हफ्ता|सप्ताह|7 दिन)\b", re.I), 7),
    (re.compile(r"\b(?:10\s*days?|das\s*din|दस दिन|10 दिन)\b", re.I), 10),
    (re.compile(r"\b(?:2\s*weeks?|do\s*hafte|14\s*days?|दो हफ्ते|2 हफ्ते|14 दिन)\b", re.I), 14),
    (re.compile(r"\b(?:next\s*month|agle\s*mahine|30\s*days?|अगले महीने|अगला महीना|30 दिन)\b", re.I), 30),
    (re.compile(r"\b(?:month|mahine|ek\s*mahina|महीना|एक महीना)\b", re.I), 30),
    (re.compile(r"\b(?:no\s*rush|anytime|when\s*possible|aaram\s*se|koi\s*jaldi\s*nahi|कोई जल्दी नहीं|आराम से)\b", re.I), 90),
]

# ---------- LANGUAGE DETECTION ----------
def _detect_language(text: str) -> str:
    if any('\u0900' <= c <= '\u097F' for c in text):
        return "hindi_devanagari"
    words = set(re.findall(r'\w+', text.lower()))
    if words & {"hai","ka","ki","ke","mein","se","shaadi","kapda","chahiye","bhai","saree","wada","kya","naram","halka","baari"}:
        return "hinglish"
    if words & {"kalyanam","pelli","pellikuturu","chira","kavali","bagundi"}:
        return "romanised_telugu"
    if words & {"pudavai","venum","romba","azhaga","nalla"}:
        return "romanised_tamil"
    if words & {"maduve","saree","beku","chennagide"}:
        return "romanised_kannada"
    if words & {"biye","bhalo","shari","chai","khub"}:
        return "romanised_bengali"
    if words & {"bibaha","bhalo","saree","dorkar"}:
        return "romanised_odia"
    return "english"

# ---------- CORE SAFE EXTRACTOR (Word Boundaries + Negation + Fuzzy) ----------
def _extract_with_aliases(text: str, alias_dict: dict, multi: bool = False):
    """
    Extracts matches using strict Unicode word boundaries to stop false positives,
    filters out negated concepts, and falls back to difflib fuzzy matching for STT typos.
    """
    matches = []
    # Regex matching negation indicators preceding an alias within ~20 chars
    negation_regex = r'\b(?:not|no|without|bina|na|chhodke|except|ban\s*on|avoid|naa|vaddu)\b'
    
    # Sort by length descending so longer compound names match before substrings
    for alias, canonical in sorted(alias_dict.items(), key=lambda x: len(x[0]), reverse=True):
        # Match using word boundaries for Latin/Devanagari scripts
        pattern = rf'(?<!\w){re.escape(alias)}(?!\w)'
        
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            # Check 20 characters preceding this match for a negation keyword
            prefix = text[max(0, m.start() - 20):m.start()]
            if not re.search(negation_regex, prefix, flags=re.IGNORECASE):
                if multi:
                    if canonical not in matches:
                        matches.append(canonical)
                else:
                    return canonical

    # Zero-Dependency Fuzzy Fallback: Catches STT spelling variations when exact regex fails
    if not matches and not multi:
        # Only fuzzy match words >= 4 characters to avoid warping prepositions
        tokens = [w for w in re.findall(r'\w+', text.lower()) if len(w) >= 4]
        for token in tokens:
            close = difflib.get_close_matches(token, [k for k in alias_dict.keys() if len(k) >= 4], n=1, cutoff=0.82)
            if close:
                # Double check that the fuzzy token wasn't negated in the text
                token_idx = text.lower().find(token)
                prefix = text[max(0, token_idx - 20):token_idx]
                if not re.search(negation_regex, prefix, flags=re.IGNORECASE):
                    return alias_dict[close[0]]

    return sorted(matches) if multi else None

# ---------- EXTRACTORS ----------
def _extract_feel(text: str) -> list[str]:
    found = set()
    negation_regex = r'\b(?:not|no|without|bina|na|avoid|vaddu)\b'
    
    for phrase, tags in sorted(FEEL_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = rf'(?<!\w){re.escape(phrase)}(?!\w)'
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            prefix = text[max(0, m.start() - 20):m.start()]
            if not re.search(negation_regex, prefix, flags=re.IGNORECASE):
                found.update(tags)
                
    for tag in _VALID_SENSORY:
        pattern = rf'(?<!\w){re.escape(tag)}(?!\w)'
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.add(tag)
            
    return sorted(found)

def _extract_occasion(text: str) -> str | None:
    return _extract_with_aliases(text, OCCASION_ALIASES, multi=False)

def _extract_color(text: str):
    negation_regex = r'\b(?:not|no|without|bina|na|except|chhodke|avoid)\b'
    for phrase, (display, family) in sorted(COLOR_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = rf'(?<!\w){re.escape(phrase)}(?!\w)'
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            prefix = text[max(0, m.start() - 20):m.start()]
            if not re.search(negation_regex, prefix, flags=re.IGNORECASE):
                return display, family
    return None, None

def _extract_location(text: str) -> str | None:
    return _extract_with_aliases(text, LOCATION_ALIASES, multi=False)

def _extract_weave(text: str) -> list[str]:
    return _extract_with_aliases(text, WEAVE_ALIASES, multi=True)

def _extract_fabric(text: str) -> list[str]:
    return _extract_with_aliases(text, FABRIC_ALIASES, multi=True)

def _extract_urgency(text: str) -> int | None:
    for pat, days in URGENCY_PATTERNS:
        if pat.search(text):
            return days
    return None

def _compute_confidence(result: IntentResult):
    score = 0.0
    missing = []
    
    # Weighted entity contribution
    if result.feel:      score += 0.25
    else:                missing.append("feel")
    if result.occasion:  score += 0.25
    else:                missing.append("occasion")
    if result.budget:    score += 0.20
    else:                missing.append("budget")
    if result.fabric:    score += 0.15
    else:                missing.append("fabric")
    if result.weave:     score += 0.05
    else:                missing.append("weave")
    if result.color:     score += 0.05
    else:                missing.append("color")
    if result.location:  score += 0.05
    else:                missing.append("location")
    
    # Penalty for contradictory extractions (e.g., both heavy and light requested)
    if "light" in result.feel and "heavy" in result.feel:
        score -= 0.15
        result.warnings.append("Contradictory feel detected (both light and heavy requested).")
    if "cotton" in result.fabric and "synthetic" in result.fabric and len(result.fabric) == 2:
        score -= 0.05
        
    # Penalty if input text is very long but few entities were safely extracted
    word_count = len(re.findall(r'\w+', result.raw_input))
    if word_count > 15 and score < 0.35:
        score -= 0.10
        result.warnings.append("Complex or noisy query syntax; key parameters obscured.")
        
    return round(max(0.0, min(1.0, score)), 2), missing

# ---------- PUBLIC API ----------
def parse_intent(raw_text: str) -> IntentResult:
    clean_text = _normalise_text(raw_text)
    result = IntentResult(raw_input=clean_text if clean_text else raw_text)
    result.language_hint = _detect_language(raw_text)
    
    # Execute safe extraction suite
    result.feel          = _extract_feel(clean_text)
    result.occasion      = _extract_occasion(clean_text)
    result.budget, result.budget_flex = _parse_budget(clean_text)
    result.color, result.color_family = _extract_color(clean_text)
    result.location      = _extract_location(clean_text)
    result.weave         = _extract_weave(clean_text)
    result.fabric        = _extract_fabric(clean_text)
    result.urgency_days  = _extract_urgency(clean_text)

    # ---- SMART DEFAULT BUDGET (When missing) ----
    if not result.budget:
        lower_text = clean_text.lower() if clean_text else ""
        is_premium_cluster = result.location in ["Varanasi", "Kanchipuram", "Venkatagiri", "Paithani", "Patola"]
        is_silk_indicated = "silk" in lower_text or "रेशम" in clean_text or "silk" in result.fabric
        
        if is_silk_indicated or is_premium_cluster or "बनारस" in clean_text or "कांची" in clean_text:
            result.budget = 6500
            result.budget_flex = True
        elif result.occasion in ["wedding", "reception"]:
            result.budget = 8000
            result.budget_flex = True
        elif result.occasion == "festival":
            result.budget = 3500
            result.budget_flex = True
        else:
            result.budget = 1800
            result.budget_flex = True

    # ---- SMART DEFAULT FEEL (When missing) ----
    if not result.feel:
        if "silk" in result.fabric or "banarasi" in result.weave or "kanjivaram" in result.weave:
            result.feel = ["rich", "elegant"]
        elif "cotton" in result.fabric or "daily_wear" == result.occasion:
            result.feel = ["comfortable", "light", "breathable"]
        elif result.location or result.color or result.weave:
            result.feel = ["comfortable", "elegant"]

    # Compute score and generate guardrail warnings
    result.confidence, result.missing = _compute_confidence(result)

    if result.budget and result.budget < 300:
        result.warnings.append(f"Budget ₹{result.budget} below minimum artisanal threshold.")
    if result.budget and result.budget > 150000:
        result.warnings.append(f"Budget ₹{result.budget} is luxury tier; bespoke lead times may apply.")
    if result.urgency_days is not None and result.urgency_days <= 2 and result.location in ["Varanasi", "Kanchipuram"]:
        result.warnings.append("High urgency requested for authentic handloom cluster; express dispatch needed.")
    if result.confidence < 0.40:
        result.warnings.append("Low confidence extraction. Ambiguous STT grammar or missing primary intents.")
        
    return result

def build_followup_question(missing: list[str]) -> str | None:
    priority = ["occasion", "fabric", "feel", "budget", "color", "location", "weave"]
    questions = {
        "occasion": "What is the primary occasion you are shopping for? (e.g., wedding, festival, daily office wear)",
        "fabric": "Do you prefer lightweight cotton, rich pure silk, or an easy-to-drape blend?",
        "feel": "How would you like the drape to feel? (e.g., light and airy, rich and structured, soft and flowy)",
        "budget": "What is your comfortable price range or budget in rupees?",
        "color": "Do you have a specific color family in mind, or should we show our trending palettes?",
        "location": "Are you looking for a specific regional weave or weaving cluster? (e.g., Banarasi, Kanjivaram, Chanderi)",
        "weave": "Any preference for the weaving artwork? (e.g., Ikat, Jamdani, Block Print, Zari border)",
    }
    for field_name in priority:
        if field_name in missing:
            return questions[field_name]
    return None
