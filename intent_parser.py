"""
Pakshi — Intent Parser (Final – robust location, colour & budget)
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

# ---------- OCCASION ALIASES ----------
OCCASION_ALIASES = {
    "wedding": "wedding", "shaadi": "wedding", "shadi": "wedding",
    "reception": "reception", "engagement": "reception",
    "festival": "festival", "puja": "festival", "pooja": "festival",
    "casual": "casual", "daily": "daily_wear", "daily wear": "daily_wear",
    "office": "work", "work": "work", "college": "college",
    "formal": "formal", "semi formal": "semi_formal",
    "ceremony": "ceremony",
    "शादी": "wedding", "विवाह": "wedding", "रिसेप्शन": "reception",
    "त्योहार": "festival", "पूजा": "festival", "दिवाली": "festival",
    "होली": "festival", "ऑफिस": "work", "कॉलेज": "college",
    "समारोह": "ceremony", "रोज़": "daily_wear", "कैज़ुअल": "casual",
    "फेस्टिवल": "festival",  # added
}

# ---------- FEEL KEYWORDS ----------
FEEL_KEYWORDS = {
    "light": ["light","airy"], "halka": ["light","airy"],
    "heavy": ["heavy","stiff"], "bhaari": ["heavy","stiff"],
    "soft": ["soft","comfortable"], "naram": ["soft"],
    "rich": ["rich","elegant"], "royal": ["royal","grand"], "shahi": ["royal","grand"],
    "luxurious": ["luxurious","rich"], "flowy": ["flowy","airy"],
    "breathable": ["breathable","airy"], "cool": ["cool","breathable"],
    "glossy": ["glossy"], "stiff": ["stiff"], "comfortable": ["comfortable"],
    "traditional": ["traditional"],
    "silk": ["rich","elegant"], "रेशम": ["rich","elegant"],
    "हल्का": ["light","airy"], "भारी": ["heavy","stiff"],
    "नरम": ["soft"], "शाही": ["royal","grand"], "शानदार": ["luxurious","rich"],
    "बहने वाला": ["flowy","airy"], "सांस लेने योग्य": ["breathable","airy"],
    "ठंडा": ["cool","breathable"], "चमकदार": ["glossy","shiny"],
    "कड़ा": ["stiff"], "आरामदायक": ["comfortable"], "पारंपरिक": ["traditional"],
}

# ---------- COLOR KEYWORDS (more inflected forms) ----------
COLOR_KEYWORDS = {
    "red": ("red","red"), "pink": ("pink","pink"), "blue": ("blue","blue"),
    "green": ("green","green"), "yellow": ("yellow","yellow"),
    "orange": ("orange","orange"), "purple": ("purple","purple"),
    "white": ("white","neutral"), "black": ("black","neutral"),
    "beige": ("beige","neutral"), "grey": ("grey","neutral"),
    "maroon": ("maroon","red"), "navy": ("navy blue","blue"),
    "teal": ("teal","green"), "mint": ("mint green","green"),
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
}

# ---------- LOCATION ALIASES (extra variants) ----------
LOCATION_ALIASES = {
    # Banaras / Varanasi
    "banaras": "Varanasi", "varanasi": "Varanasi", "kashi": "Varanasi",
    "बनारस": "Varanasi", "वाराणसी": "Varanasi", "बनारसी": "Varanasi", "काशी": "Varanasi",
    # Others
    "kanchipuram": "Kanchipuram", "कांचीपुरम": "Kanchipuram",
    "pochampally": "Pochampally", "पोचमपल्ली": "Pochampally",
    "ilkal": "Ilkal", "इलकल": "Ilkal",
    "kota": "Kota", "कोटा": "Kota",
    "chanderi": "Chanderi", "चंदेरी": "Chanderi",
    "maheshwar": "Maheshwar", "महेश्वर": "Maheshwar",
    "dharmavaram": "Dharmavaram", "धर्मावरम": "Dharmavaram",
    "mysore": "Mysore", "मैसूर": "Mysore",
    "sambalpuri": "Sambalpuri", "संबलपुर": "Sambalpuri",
    "bagru": "Bagru", "बागरू": "Bagru",
    "sanganer": "Sanganer", "संगानेर": "Sanganer",
    "kutch": "Kutch", "कच्छ": "Kutch",
    "kerala": "Kerala", "केरल": "Kerala",
    "tamil nadu": "Tamil Nadu", "तमिलनाडु": "Tamil Nadu",
    "andhra pradesh": "Andhra Pradesh", "आंध्र": "Andhra Pradesh",
    "telangana": "Telangana", "तेलंगाना": "Telangana",
    "karnataka": "Karnataka", "कर्नाटक": "Karnataka",
    "rajasthan": "Rajasthan", "राजस्थान": "Rajasthan",
    "west bengal": "West Bengal", "पश्चिम बंगाल": "West Bengal",
    "odisha": "Odisha", "उड़ीसा": "Odisha", "ओडिशा": "Odisha",
    "gujarat": "Gujarat", "गुजरात": "Gujarat",
    "maharashtra": "Maharashtra", "महाराष्ट्र": "Maharashtra",
    "bihar": "Bihar", "बिहार": "Bihar",
    "uttar pradesh": "Uttar Pradesh", "उत्तर प्रदेश": "Uttar Pradesh",
}

# ---------- BUDGET (handles Devanagari numerals) ----------
_DEVANAGARI_DIGITS = { '०':'0','१':'1','२':'2','३':'3','४':'4',
                       '५':'5','६':'6','७':'7','८':'8','९':'9' }
def _devanagari_to_arabic(s: str) -> str:
    return ''.join(_DEVANAGARI_DIGITS.get(c,c) for c in s)

def _parse_budget(text: str):
    text = _devanagari_to_arabic(text)
    text = text.lower().replace(",","")
    flex = bool(re.search(r"\b(around|approx|under|below|se kam|tak|लगभग|करीब|तक|से कम)\b", text, re.I))
    patterns = [
        (r"(?:₹|rs\.?|inr|रु\.?|रुपये?)\s*(\d+(?:\.\d+)?)\s*k", 1000),
        (r"(?:₹|rs\.?|inr|रु\.?|रुपये?)\s*(\d[\d,]*)", 1),
        (r"(\d+(?:\.\d+)?)\s*k(?:rupee|rupees?)?", 1000),
        (r"(\d[\d,]*)\s*(?:rupees?|rs\.?|inr|रुपये?|रु)", 1),
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

# ---------- URGENCY ----------
URGENCY_PATTERNS = [
    (re.compile(r"today|abhi|aaj|आज|अभी", re.I), 1),
    (re.compile(r"tomor|कल", re.I), 2),
    (re.compile(r"this\s*week|is\s*hafte|इस हफ्ते", re.I), 5),
    (re.compile(r"week|hafte|हफ्ता", re.I), 7),
    (re.compile(r"2\s*weeks?|do\s*hafte|दो हफ्ते", re.I), 14),
    (re.compile(r"next\s*month|agle\s*mahine|अगले महीने", re.I), 30),
    (re.compile(r"month|mahine|महीना", re.I), 30),
    (re.compile(r"जल्दी|urgent|जरूरी", re.I), 3),
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
    text_lower = text.lower()
    for phrase, canon in sorted(OCCASION_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in text or phrase in text_lower:
            return canon
    return None

def _extract_color(text: str):
    text_lower = text.lower()
    for phrase, (display, family) in sorted(COLOR_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in text or phrase in text_lower:
            return display, family
    return None, None

def _extract_location(text: str) -> str | None:
    text_lower = text.lower()
    for alias, canon in LOCATION_ALIASES.items():
        if alias in text or alias in text_lower:
            return canon
    return None

def _extract_urgency(text: str) -> int | None:
    for pat, days in URGENCY_PATTERNS:
        if pat.search(text):
            return days
    return None

def _compute_confidence(result: IntentResult):
    score = 0.0
    missing = []
    if result.feel: score += 0.35
    else: missing.append("feel")
    if result.occasion: score += 0.30
    else: missing.append("occasion")
    if result.budget: score += 0.25
    else: missing.append("budget")
    if result.color: score += 0.05
    else: missing.append("color")
    if result.location: score += 0.05
    else: missing.append("location")
    return round(score, 2), missing

# ---------- PUBLIC API ----------
def parse_intent(raw_text: str) -> IntentResult:
    result = IntentResult(raw_input=raw_text)
    result.language_hint = _detect_language(raw_text)
    result.feel = _extract_feel(raw_text)
    result.occasion = _extract_occasion(raw_text)
    result.budget, result.budget_flex = _parse_budget(raw_text)
    result.color, result.color_family = _extract_color(raw_text)
    result.location = _extract_location(raw_text)
    result.urgency_days = _extract_urgency(raw_text)

    # ---- DEFAULT BUDGET for silk or premium locations ----
    if not result.budget:
        # If user mentions silk, Banaras, Kanchipuram, etc., set a higher default
        lower_text = raw_text.lower()
        if ("silk" in lower_text or "रेशम" in raw_text or
            result.location in ["Varanasi", "Kanchipuram"] or
            "बनारस" in raw_text or "कांची" in raw_text):
            result.budget = 6000
            result.budget_flex = True
        elif result.occasion == "wedding":
            result.budget = 6000
            result.budget_flex = True
        else:
            # default for casual etc.
            result.budget = 1500
            result.budget_flex = True

    # ---- If no feel but we have silk or location/color, set a feel ----
    if not result.feel:
        if "silk" in raw_text.lower() or "रेशम" in raw_text:
            result.feel = ["rich", "elegant"]
        elif result.location or result.color:
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
    priority = ["feel", "occasion", "budget", "color", "location"]
    q = {
        "feel": "How do you want the fabric to feel? (light and airy, rich and heavy, soft, flowy...)",
        "occasion": "What's the occasion? (wedding, festival, casual, office...)",
        "budget": "What's your budget? (in rupees)",
        "color": "Any color preference? (or say 'no preference')",
        "location": "Any specific weaving cluster or state? (e.g. Kanchipuram, Banaras, Kota...)"
    }
    for field in priority:
        if field in missing:
            return q[field]
    return None
