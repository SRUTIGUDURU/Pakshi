"""
Pakshi — Intent Parser (Ultra‑Comprehensive – handles all dialects, misspellings, audio errors)
"""
import re
import json
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
with open(BASE_DIR / "fabric_ontology.json") as _f:
    _ONTOLOGY = json.load(_f)
_VALID_SENSORY = set()
for _fab in _ONTOLOGY["fabrics"]:
    _VALID_SENSORY.update(_fab["sensory_descriptors"])

# ---------- NORMALISATION (fix common audio & typing errors) ----------
def _normalise_text(text: str) -> str:
    """Apply dozens of common transcription / typing fixes."""
    # --- Weave fixes ---
    text = text.replace("टिकट", "इकट")      # ticket -> ikat
    text = text.replace("tikat", "ikat")
    text = text.replace("ikhat", "ikat")
    text = text.replace("icat", "ikat")
    text = text.replace("ikaat", "ikat")
    text = text.replace("इकाट", "इकट")
    # --- Budget fixes ---
    text = text.replace("आईएस", "आरएस")
    text = text.replace("आइएस", "आरएस")
    text = text.replace("rs.", "rs")
    text = text.replace("r.s.", "rs")
    text = text.replace("r s", "rs")
    # --- Location fixes ---
    text = text.replace("बनारसी", "बनारस")
    text = text.replace("बनारस", "वाराणसी")  # unify to Varanasi
    text = text.replace("वाराणसी", "बनारस")  # but we'll map both
    # --- Occasion fixes ---
    text = text.replace("वेडिंग", "शादी")
    text = text.replace("वेडींग", "शादी")
    # --- Color fixes ---
    text = text.replace("ब्लू", "नीला")
    text = text.replace("ग्रीन", "हरा")
    text = text.replace("येलो", "पीला")
    text = text.replace("रेड", "लाल")
    text = text.replace("ब्लैक", "काला")
    text = text.replace("पिंक", "गुलाबी")
    # --- Feel fixes ---
    text = text.replace("लाइट", "हल्का")
    text = text.replace("हैवी", "भारी")
    text = text.replace("सॉफ्ट", "नरम")
    text = text.replace("रिच", "शानदार")
    text = text.replace("रॉयल", "शाही")
    text = text.replace("फ्लोई", "बहने वाला")
    text = text.replace("ब्रीदेबल", "सांस लेने योग्य")
    # --- Fabric fixes ---
    text = text.replace("सिल्क", "रेशम")
    text = text.replace("कॉटन", "सूती")
    text = text.replace("सूत", "सूती")
    text = text.replace("रेशमी", "रेशम")
    return text

# ---------- OCCASION ALIASES (ultra‑expanded) ----------
OCCASION_ALIASES = {
    "wedding": "wedding", "shaadi": "wedding", "shadi": "wedding",
    "marriage": "wedding", "nikah": "wedding", "vivah": "wedding",
    "reception": "reception", "engagement": "reception", "roka": "reception",
    "festival": "festival", "puja": "festival", "pooja": "festival",
    "navratri": "festival", "dussehra": "festival", "diwali": "festival",
    "deepavali": "festival", "onam": "festival", "pongal": "festival",
    "ugadi": "festival", "sankranti": "festival", "eid": "festival",
    "durga puja": "festival", "holi": "festival", "dasara": "festival",
    "casual": "casual", "daily": "daily_wear", "daily wear": "daily_wear",
    "everyday": "daily_wear", "regular": "daily_wear", "roz ka": "daily_wear",
    "office": "work", "work": "work", "professional": "work",
    "college": "college", "university": "college", "campus": "college",
    "formal": "formal", "semi formal": "semi_formal", "party": "semi_formal",
    "ceremony": "ceremony", "gruhapravesam": "ceremony", "housewarming": "ceremony",
    "शादी": "wedding", "विवाह": "wedding", "निकाह": "wedding",
    "रिसेप्शन": "reception", "सगाई": "reception", "मंगनी": "reception",
    "त्योहार": "festival", "पूजा": "festival", "दिवाली": "festival",
    "होली": "festival", "ऑफिस": "work", "कार्यालय": "work",
    "कॉलेज": "college", "समारोह": "ceremony", "रोज़": "daily_wear",
    "कैज़ुअल": "casual", "फेस्टिवल": "festival", "फेस्टीवल": "festival",
}

# ---------- FEEL KEYWORDS (ultra‑expanded) ----------
FEEL_KEYWORDS = {
    "light": ["light","airy"], "halka": ["light","airy"],
    "heavy": ["heavy","stiff"], "bhaari": ["heavy","stiff"],
    "soft": ["soft","comfortable"], "naram": ["soft"],
    "rich": ["rich","elegant"], "royal": ["royal","grand"], "shahi": ["royal","grand"],
    "luxurious": ["luxurious","rich"], "flowy": ["flowy","airy"],
    "breathable": ["breathable","airy"], "cool": ["cool","breathable"],
    "glossy": ["glossy"], "stiff": ["stiff"], "comfortable": ["comfortable"],
    "traditional": ["traditional"], "elegant": ["elegant"],
    "silk": ["rich","elegant"], "रेशम": ["rich","elegant"],
    "हल्का": ["light","airy"], "भारी": ["heavy","stiff"],
    "नरम": ["soft"], "शाही": ["royal","grand"], "शानदार": ["luxurious","rich"],
    "बहने वाला": ["flowy","airy"], "सांस लेने योग्य": ["breathable","airy"],
    "ठंडा": ["cool","breathable"], "चमकदार": ["glossy","shiny"],
    "कड़ा": ["stiff"], "आरामदायक": ["comfortable"], "पारंपरिक": ["traditional"],
    "लाइट": ["light","airy"], "फ्लोई": ["flowy","airy"],
    "हैवी": ["heavy","stiff"], "सॉफ्ट": ["soft","comfortable"],
    "रिच": ["rich","elegant"], "रॉयल": ["royal","grand"],
}

# ---------- COLOR KEYWORDS (ultra‑expanded) ----------
COLOR_KEYWORDS = {
    "red": ("red","red"), "pink": ("pink","pink"), "blue": ("blue","blue"),
    "green": ("green","green"), "yellow": ("yellow","yellow"),
    "orange": ("orange","orange"), "purple": ("purple","purple"),
    "white": ("white","neutral"), "black": ("black","neutral"),
    "beige": ("beige","neutral"), "grey": ("grey","neutral"),
    "maroon": ("maroon","red"), "navy": ("navy blue","blue"),
    "teal": ("teal","green"), "mint": ("mint green","green"),
    "lavender": ("lavender","purple"), "lilac": ("lilac","purple"),
    "coral": ("coral","pink"), "peach": ("peach","orange"),
    "rust": ("rust","orange"), "terracotta": ("rust","orange"),
    "saffron": ("saffron","orange"), "gold": ("soft gold","yellow"),
    "champagne": ("champagne","yellow"), "ivory": ("ivory","neutral"),
    "cream": ("cream","neutral"), "brown": ("brown","neutral"),
    "लाल": ("red","red"), "गुलाबी": ("pink","pink"),
    "नीला": ("blue","blue"), "नीली": ("blue","blue"), "नीले": ("blue","blue"),
    "हरा": ("green","green"), "हरी": ("green","green"), "हरे": ("green","green"),
    "पीला": ("yellow","yellow"), "पीली": ("yellow","yellow"), "पीले": ("yellow","yellow"),
    "नारंगी": ("orange","orange"), "संतरी": ("orange","orange"),
    "बैंगनी": ("purple","purple"), "जामुनी": ("purple","purple"),
    "सफेद": ("white","neutral"), "सफ़ेद": ("white","neutral"),
    "काला": ("black","neutral"), "काली": ("black","neutral"), "काले": ("black","neutral"),
    "भूरा": ("brown","neutral"), "भूरी": ("brown","neutral"),
    "ग्रे": ("grey","neutral"), "धूसर": ("grey","neutral"),
    "ब्लू": ("blue","blue"), "ग्रीन": ("green","green"), "येलो": ("yellow","yellow"),
    "रेड": ("red","red"), "ब्लैक": ("black","neutral"),
    "पिंक": ("pink","pink"), "ऑरेंज": ("orange","orange"),
}

# ---------- LOCATION ALIASES (ultra‑expanded) ----------
LOCATION_ALIASES = {
    # Varanasi / Banaras
    "banaras": "Varanasi", "varanasi": "Varanasi", "kashi": "Varanasi",
    "बनारस": "Varanasi", "वाराणसी": "Varanasi", "बनारसी": "Varanasi", "काशी": "Varanasi",
    # Kanchipuram
    "kanchipuram": "Kanchipuram", "kancheepuram": "Kanchipuram", "kanjivaram": "Kanchipuram",
    "कांचीपुरम": "Kanchipuram", "कांची": "Kanchipuram",
    # Venkatagiri
    "venkatagiri": "Venkatagiri", "venkata giri": "Venkatagiri",
    "वेंकटागिरी": "Venkatagiri", "वेंकटगिरी": "Venkatagiri",
    # Pochampally
    "pochampally": "Pochampally", "pochampalli": "Pochampally",
    "पोचमपल्ली": "Pochampally", "पोचम्पल्ली": "Pochampally",
    # Ilkal
    "ilkal": "Ilkal", "इलकल": "Ilkal",
    # Kota
    "kota": "Kota", "कोटा": "Kota",
    # Chanderi
    "chanderi": "Chanderi", "चंदेरी": "Chanderi",
    # Maheshwar
    "maheshwar": "Maheshwar", "maheshwari": "Maheshwar",
    "महेश्वर": "Maheshwar", "महेश्वरी": "Maheshwar",
    # Dharmavaram
    "dharmavaram": "Dharmavaram", "धर्मावरम": "Dharmavaram",
    # Mysore
    "mysore": "Mysore", "मैसूर": "Mysore",
    # Sambalpuri
    "sambalpuri": "Sambalpuri", "sambalpur": "Sambalpuri",
    "संबलपुर": "Sambalpuri", "संबलपुरी": "Sambalpuri",
    # Bagru
    "bagru": "Bagru", "बागरू": "Bagru",
    # Sanganer
    "sanganer": "Sanganer", "संगानेर": "Sanganer",
    # Kutch
    "kutch": "Kutch", "कच्छ": "Kutch",
    # Kerala
    "kerala": "Kerala", "केरल": "Kerala",
    # States
    "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu",
    "तमिलनाडु": "Tamil Nadu", "तमिल": "Tamil Nadu",
    "andhra pradesh": "Andhra Pradesh", "andhra": "Andhra Pradesh",
    "आंध्र": "Andhra Pradesh", "आंध्र प्रदेश": "Andhra Pradesh",
    "telangana": "Telangana", "तेलंगाना": "Telangana",
    "karnataka": "Karnataka", "कर्नाटक": "Karnataka",
    "rajasthan": "Rajasthan", "राजस्थान": "Rajasthan",
    "west bengal": "West Bengal", "westbengal": "West Bengal",
    "पश्चिम बंगाल": "West Bengal", "बंगाल": "West Bengal",
    "odisha": "Odisha", "orissa": "Odisha",
    "उड़ीसा": "Odisha", "ओडिशा": "Odisha",
    "gujarat": "Gujarat", "गुजरात": "Gujarat",
    "maharashtra": "Maharashtra", "महाराष्ट्र": "Maharashtra",
    "bihar": "Bihar", "बिहार": "Bihar",
    "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
    "उत्तर प्रदेश": "Uttar Pradesh",
}

# ---------- WEAVE / STYLE ALIASES (ultra‑expanded) ----------
WEAVE_ALIASES = {
    # Ikat – many spellings
    "ikat": "ikat", "ikhat": "ikat", "icat": "ikat", "ikaat": "ikat",
    "इकट": "ikat", "टिकट": "ikat", "इकाट": "ikat", "ईकट": "ikat",
    # Block print
    "block print": "block print", "blockprint": "block print", "block-print": "block print",
    "ब्लॉक प्रिंट": "block print", "ब्लाक प्रिंट": "block print",
    # Jamdani
    "jamdani": "jamdani", "jhamdani": "jamdani", "जामदानी": "jamdani",
    # Kanjivaram
    "kanjivaram": "kanjivaram", "kanchipuram": "kanjivaram",
    "कांचीपुरम": "kanjivaram", "कांची": "kanjivaram",
    # Tussar
    "tussar": "tussar", "tusar": "tussar", "bhagalpuri": "tussar",
    "तुस्सर": "tussar", "तुसर": "tussar",
    # Banarasi
    "banarasi": "banarasi", "banarsi": "banarasi", "बनारसी": "banarasi",
    # Brocade
    "brocade": "brocade", "brokade": "brocade", "ब्रोकेड": "brocade",
    # Paithani
    "paithani": "paithani", "पैठणी": "paithani",
    # Patola
    "patola": "patola", "पटोला": "patola",
    # Kota Doria
    "kota doria": "kota doria", "kotadoria": "kota doria",
    "कोटा डोरिया": "kota doria",
    # Chanderi
    "chanderi": "chanderi", "chandheri": "chanderi",
    "चंदेरी": "chanderi",
    # Maheshwari
    "maheshwari": "maheshwari", "maheshwari": "maheshwari",
    "महेश्वरी": "maheshwari",
    # Sambalpuri
    "sambalpuri": "sambalpuri", "sambhalpuri": "sambalpuri",
    "संबलपुरी": "sambalpuri",
    # Ilkal
    "ilkal": "ilkal", "इलकल": "ilkal",
    # Venkatagiri
    "venkatagiri": "venkatagiri", "वेंकटागिरी": "venkatagiri",
    # Zari
    "zari": "zari", "जरी": "zari",
    # Kasavu
    "kasavu": "kasavu", "कसावु": "kasavu",
    # Temple border
    "temple border": "temple border", "templeborder": "temple border",
    "मंदिर बॉर्डर": "temple border",
    # Handloom
    "handloom": "handloom", "handwoven": "handloom", "हथकरघा": "handloom",
}

# ---------- FABRIC TYPE ALIASES (ultra‑expanded) ----------
FABRIC_ALIASES = {
    "cotton": "cotton", "suti": "cotton", "कॉटन": "cotton", "सूती": "cotton", "सूत": "cotton",
    "silk": "silk", "resham": "silk", "सिल्क": "silk", "रेशम": "silk", "रेशमी": "silk",
    "cotton silk": "cotton_silk", "cotton-silk": "cotton_silk",
    "कॉटन सिल्क": "cotton_silk", "सूती रेशम": "cotton_silk",
    "tussar": "silk", "bhagalpuri": "silk",
    "linen": "cotton", "wool": "cotton", "लिनन": "cotton", "ऊन": "cotton",
    "polyester": "cotton", "poly": "cotton", "पॉलिएस्टर": "cotton",
}

# ---------- BUDGET (handles all variants) ----------
_DEVANAGARI_DIGITS = { '०':'0','१':'1','२':'2','३':'3','४':'4',
                       '५':'5','६':'6','७':'7','८':'8','९':'9' }
def _devanagari_to_arabic(s: str) -> str:
    return ''.join(_DEVANAGARI_DIGITS.get(c,c) for c in s)

def _parse_budget(text: str):
    # Normalise budget prefixes
    text = text.replace("आईएस", "आरएस").replace("आइएस", "आरएस")
    text = text.replace("rs.", "rs").replace("r.s.", "rs").replace("r s", "rs")
    text = _devanagari_to_arabic(text)
    text = text.lower().replace(",","")
    flex = bool(re.search(r"\b(around|approx|under|below|less than|se kam|tak|लगभग|करीब|तक|से कम|अंडर|बेलो)\b", text, re.I))
    patterns = [
        (r"(?:₹|rs\.?|inr|रु\.?|रुपये?|आरएस|rs)\s*(\d+(?:\.\d+)?)\s*k", 1000),
        (r"(?:₹|rs\.?|inr|रु\.?|रुपये?|आरएस|rs)\s*(\d[\d,]*)", 1),
        (r"(\d+(?:\.\d+)?)\s*k(?:rupee|rupees?)?", 1000),
        (r"(\d[\d,]*)\s*(?:rupees?|rs\.?|inr|रुपये?|रु|आरएस|rs)", 1),
        (r"\b(\d{3,5})\b", 1),
    ]
    for pat, mult in patterns:
        m = re.search(pat, text, re.I)
        if m:
            try:
                val = float(m.group(1).replace(",","")) * mult
                b = int(val)
                if 100 <= b <= 200000:
                    return b, flex
            except: pass
    return None, False

# ---------- URGENCY (ultra‑expanded) ----------
URGENCY_PATTERNS = [
    (re.compile(r"today|abhi|aaj|आज|अभी|आज ही", re.I), 1),
    (re.compile(r"tomorrow|tomor|कल|आने वाला कल", re.I), 2),
    (re.compile(r"2\s*days?|do\s*din|दो दिन|2 दिन", re.I), 2),
    (re.compile(r"3\s*days?|teen\s*din|तीन दिन|3 दिन", re.I), 3),
    (re.compile(r"this\s*week|is\s*hafte|इस हफ्ते|इस सप्ताह", re.I), 5),
    (re.compile(r"week|hafte|हफ्ता|सप्ताह", re.I), 7),
    (re.compile(r"10\s*days?|दस दिन|10 दिन", re.I), 10),
    (re.compile(r"2\s*weeks?|do\s*hafte|दो हफ्ते|2 हफ्ते", re.I), 14),
    (re.compile(r"next\s*month|agle\s*mahine|अगले महीने|अगला महीना", re.I), 30),
    (re.compile(r"month|mahine|महीना", re.I), 30),
    (re.compile(r"जल्दी|urgent|जरूरी|asap|immediate", re.I), 3),
    (re.compile(r"no\s*rush|anytime|कोई जल्दी नहीं", re.I), 90),
]

# ---------- LANGUAGE DETECTION ----------
def _detect_language(text: str) -> str:
    if any('\u0900' <= c <= '\u097F' for c in text):
        return "hindi_devanagari"
    words = set(text.lower().split())
    if words & {"hai","ka","ki","ke","mein","se","shaadi","kapda","chahiye"}:
        return "hinglish"
    if words & {"kalyanam","pelli","pellikuturu"}:
        return "romanised_telugu"
    if words & {"kalyanam","pudavai"}:
        return "romanised_tamil"
    if words & {"maduve","saree"}:
        return "romanised_kannada"
    if words & {"biye","bhalo"}:
        return "romanised_bengali"
    if words & {"bibaha","bhalo"}:
        return "romanised_odia"
    return "english"

# ---------- HELPER FOR EXTRACTION (supports multi) ----------
def _extract_with_aliases(text: str, alias_dict: dict, multi: bool = False):
    """Extract matches using substring matching (case‑insensitive for English)."""
    text_lower = text.lower()
    matches = []
    for alias, canon in sorted(alias_dict.items(), key=lambda x: len(x[0]), reverse=True):
        # Check original (for Devanagari) and lowercased (for English)
        if alias in text or alias in text_lower:
            if multi:
                if canon not in matches:
                    matches.append(canon)
            else:
                return canon
    if multi:
        return sorted(matches)
    return None

# ---------- EXTRACTORS ----------
def _extract_feel(text: str) -> list[str]:
    found = set()
    text_lower = text.lower()
    for phrase, tags in sorted(FEEL_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in text or phrase in text_lower:
            found.update(tags)
    for tag in _VALID_SENSORY:
        if tag in text_lower:
            found.add(tag)
    return sorted(found)

def _extract_occasion(text: str) -> str | None:
    return _extract_with_aliases(text, OCCASION_ALIASES, multi=False)

def _extract_color(text: str):
    text_lower = text.lower()
    for phrase, (display, family) in sorted(COLOR_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in text or phrase in text_lower:
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
    if result.feel: score += 0.30
    else: missing.append("feel")
    if result.occasion: score += 0.25
    else: missing.append("occasion")
    if result.budget: score += 0.20
    else: missing.append("budget")
    if result.color: score += 0.05
    else: missing.append("color")
    if result.location: score += 0.05
    else: missing.append("location")
    if result.weave: score += 0.05
    else: missing.append("weave")
    if result.fabric: score += 0.05
    else: missing.append("fabric")
    return round(score, 2), missing

# ---------- PUBLIC API ----------
def parse_intent(raw_text: str) -> IntentResult:
    raw_text = _normalise_text(raw_text)
    result = IntentResult(raw_input=raw_text)
    result.language_hint = _detect_language(raw_text)
    result.feel = _extract_feel(raw_text)
    result.occasion = _extract_occasion(raw_text)
    result.budget, result.budget_flex = _parse_budget(raw_text)
    result.color, result.color_family = _extract_color(raw_text)
    result.location = _extract_location(raw_text)
    result.weave = _extract_weave(raw_text)
    result.fabric = _extract_fabric(raw_text)
    result.urgency_days = _extract_urgency(raw_text)

    # ---- DEFAULT BUDGET ----
    if not result.budget:
        lower_text = raw_text.lower()
        if ("silk" in lower_text or "रेशम" in raw_text or
            result.location in ["Varanasi", "Kanchipuram", "Venkatagiri"] or
            "बनारस" in raw_text or "कांची" in raw_text or "वेंकट" in raw_text):
            result.budget = 6000
            result.budget_flex = True
        elif result.occasion == "wedding":
            result.budget = 6000
            result.budget_flex = True
        else:
            result.budget = 1500
            result.budget_flex = True

    # ---- DEFAULT FEEL ----
    if not result.feel:
        if "silk" in raw_text.lower() or "रेशम" in raw_text:
            result.feel = ["rich", "elegant"]
        elif result.location or result.color or result.weave:
            result.feel = ["comfortable", "elegant"]

    result.confidence, result.missing = _compute_confidence(result)

    if result.budget and result.budget < 300:
        result.warnings.append(f"Budget ₹{result.budget} below minimum.")
    if result.budget and result.budget > 20000:
        result.warnings.append(f"Budget ₹{result.budget} is premium, lead time may be longer.")
    if result.confidence < 0.4:
        result.warnings.append("Low confidence. Ask for more details.")
    return result

def build_followup_question(missing: list[str]) -> str | None:
    priority = ["feel", "occasion", "budget", "color", "location", "weave", "fabric"]
    q = {
        "feel": "How do you want the fabric to feel? (light and airy, rich and heavy, soft, flowy...)",
        "occasion": "What's the occasion? (wedding, festival, casual, office...)",
        "budget": "What's your budget? (in rupees)",
        "color": "Any color preference? (or say 'no preference')",
        "location": "Any specific weaving cluster or state? (e.g. Kanchipuram, Banaras, Kota...)",
        "weave": "Any specific weave or style? (ikat, block print, jamdani, etc.)",
        "fabric": "Do you prefer cotton, silk, or a blend?",
    }
    for field in priority:
        if field in missing:
            return q[field]
    return None
