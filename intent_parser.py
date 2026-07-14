"""
Pakshi — Intent Parser (Devanagari‑Enhanced)
=============================================
Converts raw buyer text (any Indian language, romanised, or English)
into a structured intent dict consumed by retrieval.py.

Now with comprehensive Devanagari support for:
  - sensory words (feel)
  - occasions
  - colours
  - locations (clusters and states)
  - budget (including Devanagari numerals)
  - urgency

Pipeline:
  raw text → language detection → keyword normalisation
           → feel extraction → occasion mapping → budget extraction
           → color extraction → location extraction → urgency detection
           → confidence scoring → structured IntentResult
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IntentResult:
    feel:          list[str]       = field(default_factory=list)
    occasion:      str | None      = None
    budget:        int | None      = None
    budget_flex:   bool            = False   # True if "around", "approx" etc.
    color:         str | None      = None
    color_family:  str | None      = None
    location:      str | None      = None    # NEW: extracted from text
    urgency_days:  int | None      = None    # max delivery days acceptable
    language_hint: str             = "english"
    raw_input:     str             = ""
    confidence:    float           = 0.0     # 0.0 – 1.0
    missing:       list[str]       = field(default_factory=list)  # fields we couldn't extract
    warnings:      list[str]       = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Knowledge bases (pulled from fabric_ontology.json + hand-crafted)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "fabric_ontology.json") as _f:
    _ONTOLOGY = json.load(_f)

# All valid sensory tags from ontology
_VALID_SENSORY: set[str] = set()
for _fab in _ONTOLOGY["fabrics"]:
    _VALID_SENSORY.update(_fab["sensory_descriptors"])


# ===========================================================================
# 1. OCCASION ALIASES  (alias → canonical occasion tag)
#    Massive expansion with Devanagari, romanised Indian languages.
# ===========================================================================
OCCASION_ALIASES: dict[str, str] = {
    # ── Wedding ──
    "wedding":          "wedding",
    "shaadi":           "wedding",
    "shadi":            "wedding",
    "vivah":            "wedding",
    "marriage":         "wedding",
    "nikah":            "wedding",
    # Hindi Devanagari
    "शादी":             "wedding",
    "वेडिंग":           "wedding",
    "विवाह":            "wedding",
    "निकाह":            "wedding",
    # Telugu wedding
    "pellikuturu":      "wedding",
    "pelliki":          "wedding",
    "pelli":            "wedding",
    # Tamil wedding
    "kalyanam":         "wedding",
    # Kannada wedding
    "maduve":           "wedding",
    # Bengali wedding
    "biye":             "wedding",
    # Odia wedding
    "bibaha":           "wedding",
    "lagna":            "wedding",

    # ── Reception / Engagement ──
    "reception":        "reception",
    "engagement":       "reception",
    "roka":             "reception",
    "मंगनी":            "reception",
    "सगाई":             "reception",
    "रिसेप्शन":         "reception",

    # ── Festival ──
    "festival":         "festival",
    "puja":             "festival",
    "pooja":            "festival",
    "navratri":         "festival",
    "dussehra":         "festival",
    "diwali":           "festival",
    "deepavali":        "festival",   # Tamil
    "onam":             "festival",
    "pongal":           "festival",   # Tamil
    "ugadi":            "festival",   # Telugu/Kannada
    "sankranti":        "festival",   # Telugu/Kannada/Odia
    "eid":              "festival",
    "durga puja":       "festival",   # Bengali/Odia
    "poila boishakh":   "festival",   # Bengali New Year
    "ganesh chaturthi": "festival",
    "holi":             "festival",
    "dasara":           "festival",   # Kannada
    # Odia festivals
    "nuakhai":          "festival",
    "raja":             "festival",
    # Devanagari
    "त्योहार":          "festival",
    "पूजा":             "festival",
    "नवरात्रि":         "festival",
    "दशहरा":            "festival",
    "दिवाली":           "festival",
    "दीपावली":          "festival",
    "ओणम":              "festival",
    "पोंगल":            "festival",
    "उगादी":            "festival",
    "संक्रांति":        "festival",
    "ईद":               "festival",
    "दुर्गा पूजा":      "festival",
    "गणेश चतुर्थी":    "festival",
    "होली":             "festival",

    # ── Casual / Daily ──
    "casual":           "casual",
    "daily":            "daily_wear",
    "daily wear":       "daily_wear",
    "everyday":         "daily_wear",
    "regular":          "daily_wear",
    "roz ka":           "daily_wear",
    "rozana":           "daily_wear",
    "normal":           "daily_wear",
    # Devanagari
    "कैज़ुअल":          "casual",
    "दैनिक":            "daily_wear",
    "रोज़":             "daily_wear",
    "रोज":              "daily_wear",
    "नॉर्मल":           "daily_wear",

    # ── Work / Office ──
    "office":           "work",
    "work":             "work",
    "professional":     "work",
    "formal":           "formal",
    "meeting":          "work",
    "conference":       "work",
    # Devanagari
    "ऑफिस":             "work",
    "कार्यालय":         "work",
    "प्रोफेशनल":       "work",
    "मीटिंग":           "work",

    # ── College / Young ──
    "college":          "college",
    "university":       "college",
    "campus":           "college",
    "class":            "college",
    # Devanagari
    "कॉलेज":            "college",
    "यूनिवर्सिटी":     "college",

    # ── Summer ──
    "summer":           "summer",
    "summer wedding":   "summer_wedding",
    "beach":            "summer",
    "grishma":          "summer",
    "गर्मी":            "summer",

    # ── Semi-formal ──
    "semi formal":      "semi_formal",
    "semi-formal":      "semi_formal",
    "party":            "semi_formal",
    "get together":     "semi_formal",

    # ── Ceremony ──
    "ceremony":         "ceremony",
    "gruhapravesam":    "ceremony",
    "housewarming":     "ceremony",
    "baby shower":      "ceremony",
    "seemantham":       "ceremony",
    # Devanagari
    "समारोह":           "ceremony",
    "गृहप्रवेश":       "ceremony",
    "बेबी शावर":       "ceremony",
}


# ===========================================================================
# 2. FEEL / SENSORY KEYWORDS (keyword → list of feel tags)
#    Massive expansion with Devanagari and regional language words.
# ===========================================================================
FEEL_KEYWORDS: dict[str, list[str]] = {
    # ── Lightness ──
    "light":            ["light", "airy"],
    "lightweight":      ["light", "airy"],
    "halka":            ["light", "airy"],
    "hafif":            ["light"],
    "airy":             ["airy", "breathable"],
    "breathable":       ["breathable", "airy"],
    "flowy":            ["flowy", "airy"],
    "flowy fabric":     ["flowy"],
    "fluttery":         ["flowy", "airy"],
    "breezy":           ["airy", "breathable", "cool"],
    "cool":             ["cool", "breathable"],
    "thanda":           ["cool", "breathable"],
    # Devanagari
    "हल्का":            ["light", "airy"],
    "हल्की":            ["light", "airy"],
    "हवादार":          ["airy", "breathable"],
    "सांस लेने योग्य": ["breathable", "airy"],
    "बहने वाला":       ["flowy", "airy"],
    "ठंडा":             ["cool", "breathable"],
    "ठंडी":             ["cool", "breathable"],

    # ── Softness / comfort ──
    "soft":             ["soft", "comfortable"],
    "naram":            ["soft"],
    "comfortable":      ["comfortable"],
    "comfortable fabric":["comfortable"],
    "easy":             ["comfortable", "everyday"],
    "cozy":             ["comfortable", "soft"],
    # Telugu: good / nice → soft/comfortable
    "manchidi":         ["comfortable", "soft"],
    # Odia: good / nice → soft/comfortable
    "bhalo":            ["comfortable", "soft"],
    # Devanagari
    "नरम":              ["soft"],
    "मुलायम":           ["soft", "comfortable"],
    "सुविधाजनक":        ["comfortable"],
    "आरामदायक":         ["comfortable"],
    "आरामदायी":         ["comfortable"],

    # ── Richness / formality ──
    "rich":             ["rich", "elegant"],
    "luxurious":        ["luxurious", "rich"],
    "luxury":           ["luxurious", "rich"],
    "grand":            ["grand", "royal"],
    "royal":            ["royal", "grand"],
    "shahi":            ["royal", "grand"],
    "elegant":          ["elegant"],
    "classy":           ["elegant", "rich"],
    "graceful":         ["elegant", "flowy"],
    # Devanagari
    "शाही":             ["royal", "grand"],
    "शानदार":           ["luxurious", "rich"],
    "भव्य":             ["grand", "royal"],
    "राजसी":            ["royal", "grand"],
    "सुंदर":            ["elegant"],
    "क्लासी":           ["elegant", "rich"],
    "गरिमामय":          ["elegant"],

    # ── Sheen / finish ──
    "shiny":            ["glossy", "shiny"],
    "glossy":           ["glossy"],
    "matte":            ["matte"],
    "shimmer":          ["glossy", "shiny"],
    "glitter":          ["glossy"],
    "dull":             ["matte"],
    # Devanagari
    "चमकदार":          ["glossy", "shiny"],
    "मैट":              ["matte"],

    # ── Weight ──
    "heavy":            ["heavy", "stiff"],
    "bhaari":           ["heavy"],
    "stiff":            ["stiff"],
    "structured":       ["stiff", "structured"],
    "thick":            ["heavy"],
    # Devanagari
    "भारी":             ["heavy", "stiff"],
    "मोटा":             ["heavy"],
    "कड़ा":             ["stiff"],
    "संरचित":           ["stiff", "structured"],

    # ── Occasion-derived feel ──
    "wedding fabric":   ["elegant", "rich"],
    "bridal":           ["luxurious", "rich", "royal"],
    "party wear":       ["elegant", "semi-formal"],
    "traditional":      ["traditional"],
    "ethnic":           ["traditional"],
    "desi":             ["traditional"],
    "fusion":           ["versatile"],
    "modern":           ["versatile"],
    "indo western":     ["versatile"],
    # Devanagari
    "पारंपरिक":         ["traditional"],
    "एथनिक":            ["traditional"],
    "फ्यूजन":           ["versatile"],

    # ── Sensory metaphors ──
    "summer wedding":   ["flowy", "breathable yet elegant", "light but rich"],
    "not too heavy":    ["light", "comfortable"],
    "not too stiff":    ["flowy", "soft"],
    "drapes well":      ["flowy"],
    "good drape":       ["flowy"],
    "falls nicely":     ["flowy"],
    "skin friendly":    ["breathable", "soft", "comfortable"],
    "non itchy":        ["soft", "comfortable"],
    "everyday silk":    ["soft sheen", "comfortable formal"],
    "budget silk":      ["soft sheen", "light but rich"],
    "feels like silk":  ["soft sheen", "flowy"],
}


# ===========================================================================
# 3. COLOR KEYWORDS (keyword → (display_name, color_family))
#    Comprehensive: Devanagari, romanised, and English.
# ===========================================================================
COLOR_KEYWORDS: dict[str, tuple[str, str]] = {
    # ── RED ──
    "red":          ("red", "red"),
    "dark red":     ("dark red", "red"),
    "deep red":     ("deep red", "red"),
    "maroon":       ("maroon", "red"),
    "burgundy":     ("maroon", "red"),
    "wine":         ("wine red", "red"),
    "crimson":      ("crimson", "red"),
    "vermillion":   ("vermillion red", "red"),
    "laal":         ("red", "red"),               # Hindi (romanised)
    "surkh":        ("red", "red"),               # Urdu
    "erupu":        ("red", "red"),               # Telugu
    "sivappu":      ("red", "red"),               # Tamil
    "kempu":        ("red", "red"),               # Kannada
    "lal":          ("red", "red"),               # Bengali / Odia
    # Devanagari
    "लाल":          ("red", "red"),
    "लाल रंग":      ("red", "red"),
    "गहरा लाल":     ("deep red", "red"),
    "मरून":         ("maroon", "red"),
    "बरगंडी":       ("maroon", "red"),

    # ── PINK ──
    "pink":         ("pink", "pink"),
    "light pink":   ("pale pink", "pink"),
    "pale pink":    ("pale pink", "pink"),
    "dusty rose":   ("dusty rose", "pink"),
    "rose":         ("dusty rose", "pink"),
    "blush":        ("pale pink", "pink"),
    "magenta":      ("magenta", "pink"),
    "hot pink":     ("magenta", "pink"),
    "coral":        ("coral", "pink"),
    "gulaabi":      ("pink", "pink"),             # Hindi (romanised)
    # Devanagari
    "गुलाबी":       ("pink", "pink"),
    "हल्की गुलाबी": ("pale pink", "pink"),
    "मैजेंटा":      ("magenta", "pink"),
    "कोरल":         ("coral", "pink"),

    # ── ORANGE ──
    "orange":       ("orange", "orange"),
    "saffron":      ("saffron", "orange"),
    "kesari":       ("saffron", "orange"),        # Hindi (romanised)
    "peach":        ("peach", "orange"),
    "rust":         ("rust", "orange"),
    "terracotta":   ("rust", "orange"),
    "kumkum":       ("saffron", "orange"),        # Telugu/Tamil/Kannada
    # Devanagari
    "नारंगी":       ("orange", "orange"),
    "केसरिया":      ("saffron", "orange"),
    "पीच":          ("peach", "orange"),
    "जंग":          ("rust", "orange"),

    # ── YELLOW ──
    "yellow":       ("yellow", "yellow"),
    "mustard":      ("mustard yellow", "yellow"),
    "golden":       ("soft gold", "yellow"),
    "gold":         ("soft gold", "yellow"),
    "pale gold":    ("pale gold", "yellow"),
    "champagne":    ("champagne", "yellow"),
    "ivory":        ("ivory", "neutral"),
    "pila":         ("yellow", "yellow"),          # Hindi (romanised)
    "pillu":        ("yellow", "yellow"),          # Telugu
    "manjal":       ("yellow", "yellow"),          # Tamil
    "haladi":       ("yellow", "yellow"),          # Kannada
    "holud":        ("yellow", "yellow"),          # Bengali
    "pila":         ("yellow", "yellow"),          # Odia
    # Devanagari
    "पीला":         ("yellow", "yellow"),
    "पीली":         ("yellow", "yellow"),
    "पीला रंग":     ("yellow", "yellow"),
    "सरसों":        ("mustard yellow", "yellow"),
    "गोल्डन":       ("soft gold", "yellow"),
    "सोना":         ("soft gold", "yellow"),
    "शैम्पेन":      ("champagne", "yellow"),
    "हाथी दाँत":    ("ivory", "neutral"),

    # ── GREEN ──
    "green":        ("green", "green"),
    "dark green":   ("dark green", "green"),
    "deep green":   ("deep green", "green"),
    "light green":  ("light green", "green"),
    "mint":         ("mint green", "green"),
    "mint green":   ("mint green", "green"),
    "sage":         ("sage green", "green"),
    "teal":         ("teal", "green"),
    "olive":        ("olive", "green"),
    "jade":         ("jade green", "green"),
    "bottle green": ("dark green", "green"),
    "forest green": ("dark green", "green"),
    "hara":         ("green", "green"),            # Hindi (romanised)
    "mehendi":      ("dark green", "green"),       # Hindi (romanised)
    "pacha":        ("green", "green"),            # Telugu
    "pachchai":     ("green", "green"),            # Tamil
    "hasiru":       ("green", "green"),            # Kannada
    "sobuj":        ("green", "green"),            # Bengali
    "haria":        ("green", "green"),            # Odia
    # Devanagari
    "हरा":          ("green", "green"),
    "हरी":          ("green", "green"),
    "हरा रंग":      ("green", "green"),
    "गहरा हरा":     ("dark green", "green"),
    "हल्का हरा":    ("light green", "green"),
    "पुदीना":       ("mint green", "green"),
    "ऋषि":          ("sage green", "green"),
    "नील":          ("teal", "green"),
    "जैतून":        ("olive", "green"),
    "जेड":          ("jade green", "green"),

    # ── BLUE ──
    "blue":         ("blue", "blue"),
    "dark blue":    ("navy blue", "blue"),
    "navy":         ("navy blue", "blue"),
    "navy blue":    ("navy blue", "blue"),
    "royal blue":   ("royal blue", "blue"),
    "sky blue":     ("sky blue", "blue"),
    "light blue":   ("pale blue", "blue"),
    "pale blue":    ("pale blue", "blue"),
    "powder blue":  ("pale blue", "blue"),
    "cobalt":       ("royal blue", "blue"),
    "peacock blue": ("peacock blue", "blue"),
    "aqua":         ("aqua", "blue"),
    "turquoise":    ("turquoise", "blue"),
    "neela":        ("blue", "blue"),             # Hindi (romanised)
    "neelam":       ("blue", "blue"),             # Telugu
    "neel":         ("blue", "blue"),             # Bengali / Odia
    "neeli":        ("blue", "blue"),             # Kannada
    # Devanagari
    "नीला":         ("blue", "blue"),
    "नीली":         ("blue", "blue"),
    "नीला रंग":     ("blue", "blue"),
    "गहरा नीला":    ("navy blue", "blue"),
    "शाही नीला":    ("royal blue", "blue"),
    "आसमानी":       ("sky blue", "blue"),
    "हल्का नीला":   ("pale blue", "blue"),
    "मोर नीला":     ("peacock blue", "blue"),
    "फ़िरोज़ा":     ("turquoise", "blue"),

    # ── PURPLE ──
    "purple":       ("purple", "purple"),
    "violet":       ("purple", "purple"),
    "lavender":     ("lavender", "purple"),
    "lilac":        ("lilac", "purple"),
    "deep purple":  ("deep purple", "purple"),
    "plum":         ("deep purple", "purple"),
    "mauve":        ("lilac", "purple"),
    "baingani":     ("purple", "purple"),         # Hindi (romanised)
    # Devanagari
    "बैंगनी":       ("purple", "purple"),
    "जामुनी":       ("purple", "purple"),
    "बैंगनी":       ("purple", "purple"),
    "गहरा बैंगनी": ("deep purple", "purple"),
    "लैवेंडर":      ("lavender", "purple"),
    "लाइलैक":       ("lilac", "purple"),

    # ── NEUTRAL (white, cream, beige, black, grey) ──
    "white":        ("white", "neutral"),
    "cream":        ("cream", "neutral"),
    "off white":    ("off-white", "neutral"),
    "off-white":    ("off-white", "neutral"),
    "beige":        ("beige", "neutral"),
    "nude":         ("beige", "neutral"),
    "natural":      ("natural beige", "neutral"),
    "brown":        ("natural beige", "neutral"),
    "safed":        ("white", "neutral"),         # Hindi (romanised)
    "tella":        ("white", "neutral"),         # Telugu
    "vella":        ("white", "neutral"),         # Tamil
    "bili":         ("white", "neutral"),         # Kannada
    "shada":        ("white", "neutral"),         # Bengali
    "dhala":        ("white", "neutral"),         # Odia
    "black":        ("black", "neutral"),
    "grey":         ("grey", "neutral"),
    "gray":         ("grey", "neutral"),
    "kala":         ("black", "neutral"),         # Hindi (romanised)
    "nalla":        ("black", "neutral"),         # Telugu
    "karuppu":      ("black", "neutral"),         # Tamil
    "kappu":        ("black", "neutral"),         # Kannada
    "kalo":         ("black", "neutral"),         # Bengali
    "kala":         ("black", "neutral"),         # Odia
    # Devanagari
    "सफेद":         ("white", "neutral"),
    "सफेद रंग":     ("white", "neutral"),
    "क्रीम":         ("cream", "neutral"),
    "मलाई":         ("cream", "neutral"),
    "बेज":          ("beige", "neutral"),
    "भूरा":         ("natural beige", "neutral"),
    "काला":         ("black", "neutral"),
    "काली":         ("black", "neutral"),
    "काला रंग":     ("black", "neutral"),
    "ग्रे":          ("grey", "neutral"),
    "धूसर":         ("grey", "neutral"),

    # ── Vague / descriptive ──
    "pastel":       ("pastel", "neutral"),
    "pastels":      ("pastel", "neutral"),
    "light colour": ("pastel", "neutral"),
    "light color":  ("pastel", "neutral"),
    "dark":         ("dark", "neutral"),
    "dark colour":  ("dark", "neutral"),
    "bright":       ("bright", "neutral"),
    "earthy":       ("natural beige", "neutral"),
    "earth tones":  ("natural beige", "neutral"),
    "neutral":      ("neutral", "neutral"),
    "muted":        ("muted", "neutral"),
}


# ===========================================================================
# 4. LOCATION ALIASES (alias → canonical cluster/state name)
#    Includes Devanagari and romanised versions.
# ===========================================================================
LOCATION_ALIASES: dict[str, str] = {
    # Clusters (English / Romanised)
    "kanchipuram": "Kanchipuram",
    "kancheepuram": "Kanchipuram",
    "pochampally": "Pochampally",
    "pochampalli": "Pochampally",
    "banarasi": "Varanasi",
    "varanasi": "Varanasi",
    "ilkal": "Ilkal",
    "kota": "Kota",
    "chanderi": "Chanderi",
    "maheshwar": "Maheshwar",
    "maheshwari": "Maheshwar",
    "dharmavaram": "Dharmavaram",
    "molakalmuru": "Molakalmuru",
    "mysore": "Mysore",
    "sambalpur": "Sambalpuri",
    "sambalpuri": "Sambalpuri",
    "nuapatna": "Nuapatna",
    "bagru": "Bagru",
    "sanganer": "Sanganer",
    "kutch": "Kutch",
    "kerala": "Kerala",
    "tamilnadu": "Tamil Nadu",
    "tamil nadu": "Tamil Nadu",
    "andhra": "Andhra Pradesh",
    "andhra pradesh": "Andhra Pradesh",
    "telangana": "Telangana",
    "karnataka": "Karnataka",
    "rajasthan": "Rajasthan",
    "west bengal": "West Bengal",
    "bengal": "West Bengal",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "gujarat": "Gujarat",
    "maharashtra": "Maharashtra",
    "bihar": "Bihar",
    "uttar pradesh": "Uttar Pradesh",
    # Devanagari
    "कांचीपुरम": "Kanchipuram",
    "पोचमपल्ली": "Pochampally",
    "बनारसी": "Varanasi",
    "वाराणसी": "Varanasi",
    "इलकल": "Ilkal",
    "कोटा": "Kota",
    "चंदेरी": "Chanderi",
    "महेश्वर": "Maheshwar",
    "धर्मावरम": "Dharmavaram",
    "मैसूर": "Mysore",
    "संबलपुर": "Sambalpuri",
    "बागरू": "Bagru",
    "संगानेर": "Sanganer",
    "कच्छ": "Kutch",
    "केरल": "Kerala",
    "तमिलनाडु": "Tamil Nadu",
    "आंध्र": "Andhra Pradesh",
    "आंध्र प्रदेश": "Andhra Pradesh",
    "तेलंगाना": "Telangana",
    "कर्नाटक": "Karnataka",
    "राजस्थान": "Rajasthan",
    "पश्चिम बंगाल": "West Bengal",
    "बंगाल": "West Bengal",
    "उड़ीसा": "Odisha",
    "ओडिशा": "Odisha",
    "गुजरात": "Gujarat",
    "महाराष्ट्र": "Maharashtra",
    "बिहार": "Bihar",
    "उत्तर प्रदेश": "Uttar Pradesh",
}


# ===========================================================================
# 5. BUDGET PATTERNS – now also handles Devanagari numerals
# ===========================================================================
_DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
}

def _devanagari_to_arabic(s: str) -> str:
    """Convert Devanagari digits to Arabic numerals."""
    return ''.join(_DEVANAGARI_DIGITS.get(c, c) for c in s)


def _parse_budget(text: str) -> tuple[int | None, bool]:
    """
    Returns (budget_inr, is_flexible).
    is_flexible = True when phrasing suggests "around/approx/under".
    Handles Devanagari script and numerals.
    """
    # First, convert Devanagari digits to Arabic
    text = _devanagari_to_arabic(text)
    text = text.lower().replace(",", "")

    flex_words = re.compile(
        r"\b(around|approx|approximately|about|roughly|nearly|"
        r"lagbhag|kaafi|under|below|less than|se kam|tak|upto|up to|"
        r"लगभग|करीब|क़रीब|तक|से कम|अंडर|बेलो|क़रीबन)\b",
        re.I
    )
    is_flexible = bool(flex_words.search(text))

    # Patterns ranked by specificity
    patterns = [
        # ₹1,500 or Rs 1500
        (r"(?:₹|rs\.?|inr|रु\.?|रुपये?)\s*(\d+(?:\.\d+)?)\s*k",    1000),
        (r"(?:₹|rs\.?|inr|रु\.?|रुपये?)\s*(\d[\d,]*)",              1),
        # "1.5k" or "2k"
        (r"(\d+(?:\.\d+)?)\s*k(?:rupee|rupees?)?",      1000),
        # "1500 rupees" or "1500 rs"
        (r"(\d[\d,]*)\s*(?:rupees?|rs\.?|inr|रुपये?|रु)",         1),
        # bare number that looks like a price (300–99999)
        (r"\b(\d{3,5})\b",                              1),
    ]

    for pattern, multiplier in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            try:
                val = float(m.group(1).replace(",", "")) * multiplier
                budget = int(val)
                if 100 <= budget <= 200_000:   # sanity check
                    return budget, is_flexible
            except ValueError:
                continue

    return None, False


# ===========================================================================
# 6. URGENCY PATTERNS (including Devanagari)
# ===========================================================================
URGENCY_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"today|abhi|aaj|आज|अभी",            re.I), 1),
    (re.compile(r"tomor|कल|tomorrow",                re.I), 2),
    (re.compile(r"2\s*days?|do\s*din|दो दिन",        re.I), 2),
    (re.compile(r"3\s*days?|teen\s*din|तीन दिन",     re.I), 3),
    (re.compile(r"this\s*week|is\s*hafte|इस हफ्ते",  re.I), 5),
    (re.compile(r"week|hafte|हफ्ता",                 re.I), 7),
    (re.compile(r"10\s*days?|दस दिन",                re.I), 10),
    (re.compile(r"2\s*weeks?|do\s*hafte|दो हफ्ते",   re.I), 14),
    (re.compile(r"next\s*month|agle\s*mahine|अगले महीने", re.I), 30),
    (re.compile(r"month|mahine|महीना",               re.I), 30),
    (re.compile(r"no\s*rush|anytime|कोई जल्दी नहीं", re.I), 90),
    (re.compile(r"जल्दी|उर्जेंट|urgent|जरूरी",      re.I), 3),
]


# ===========================================================================
# 7. LANGUAGE DETECTION (now marks Devanagari script)
# ===========================================================================
_HINDI_MARKERS   = {"hai", "ka", "ki", "ke", "mein", "se", "koi", "bahut",
                    "acha", "thoda", "shaadi", "kapda", "lena", "chahiye",
                    "rupaye", "halka", "bhaari", "naram", "laal", "safed"}

_HINDI_DEVANAGARI_MARKERS = {"है", "का", "की", "के", "में", "से", "कोई", "बहुत",
                             "अच्छा", "थोड़ा", "शादी", "कपड़ा", "लेना", "चाहिए",
                             "रुपये", "हल्का", "भारी", "नरम", "लाल", "सफेद"}

_TELUGU_MARKERS  = {"kalyanam", "pellikuturu", "pelli", "saree", "chali",
                    "manchidi", "erupu", "pacha", "tella", "neelam", "nalla",
                    "pillu", "ugadi", "sankranti"}

_TAMIL_MARKERS   = {"kalyanam", "pudavai", "nalla", "romba", "saree",
                    "sivappu", "pachchai", "vella", "neelam", "karuppu",
                    "pongal", "deepavali", "manjal"}

_KANNADA_MARKERS = {"maduve", "saree", "chennagide", "kempu", "hasiru",
                    "bili", "neeli", "kappu", "dasara", "sankranti", "haladi"}

_BENGALI_MARKERS = {"biye", "saree", "khoob", "sundor", "bhalo", "shada",
                    "lal", "sobuj", "neel", "kalo", "holud", "durga puja"}

_ODIA_MARKERS    = {"bibaha", "saree", "bhalo", "dhala", "lal", "haria",
                    "neela", "kala", "pila", "nuakhai", "raja", "puja"}


def _detect_language(text: str) -> str:
    words = set(text.lower().split())
    # Check for Devanagari script presence
    devanagari_chars = any('\u0900' <= c <= '\u097F' for c in text)
    if devanagari_chars:
        return "hindi_devanagari"
    if words & _HINDI_MARKERS:
        return "hinglish"
    if words & _TELUGU_MARKERS:
        return "romanised_telugu"
    if words & _TAMIL_MARKERS:
        return "romanised_tamil"
    if words & _KANNADA_MARKERS:
        return "romanised_kannada"
    if words & _BENGALI_MARKERS:
        return "romanised_bengali"
    if words & _ODIA_MARKERS:
        return "romanised_odia"
    return "english"


# ===========================================================================
# 8. EXTRACTION FUNCTIONS
# ===========================================================================

def _extract_feel(text: str) -> list[str]:
    """Multi-word phrases first, then single words."""
    found: set[str] = set()
    text_lower = text.lower()

    # Sort by phrase length descending so multi-word matches win
    for phrase, tags in sorted(FEEL_KEYWORDS.items(),
                               key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
            found.update(tags)

    # Fallback: check individual sensory tags from ontology directly
    for tag in _VALID_SENSORY:
        if re.search(r'\b' + re.escape(tag) + r'\b', text_lower):
            found.add(tag)

    return sorted(found)


def _extract_occasion(text: str) -> str | None:
    """Returns canonical occasion tag or None."""
    text_lower = text.lower()
    for phrase, canonical in sorted(OCCASION_ALIASES.items(),
                                    key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
            return canonical
    return None


def _extract_color(text: str) -> tuple[str | None, str | None]:
    """Returns (color_display_name, color_family) or (None, None)."""
    text_lower = text.lower()
    # Multi-word colors first
    for phrase, (display, family) in sorted(COLOR_KEYWORDS.items(),
                                            key=lambda x: len(x[0]), reverse=True):
        if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
            return display, family
    return None, None


def _extract_location(text: str) -> str | None:
    """Extract a location (cluster or state) from buyer text."""
    text_lower = text.lower()
    for alias, canonical in LOCATION_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
            return canonical
    return None


def _extract_urgency(text: str) -> int | None:
    """Returns max acceptable delivery days or None."""
    for pattern, days in URGENCY_PATTERNS:
        if pattern.search(text):
            return days
    return None


def _compute_confidence(result: IntentResult) -> tuple[float, list[str]]:
    """
    Returns (confidence_score, list_of_missing_fields).
    Scoring: feel=40pts, occasion=30pts, budget=20pts, color=5pts, location=5pts.
    """
    score = 0.0
    missing = []

    if result.feel:
        score += 0.40
    else:
        missing.append("feel")

    if result.occasion:
        score += 0.30
    else:
        missing.append("occasion")

    if result.budget:
        score += 0.20
    else:
        missing.append("budget")

    if result.color:
        score += 0.05
    else:
        missing.append("color")

    if result.location:
        score += 0.05
    else:
        missing.append("location")

    return round(score, 2), missing


# ===========================================================================
# 9. PUBLIC API
# ===========================================================================

def parse_intent(raw_text: str) -> IntentResult:
    """
    Main entry point. Takes raw buyer text and returns IntentResult.
    """
    result = IntentResult(raw_input=raw_text)

    # 1. Language detection
    result.language_hint = _detect_language(raw_text)

    # 2. Feel extraction
    result.feel = _extract_feel(raw_text)

    # 3. Occasion extraction
    result.occasion = _extract_occasion(raw_text)

    # 4. Budget extraction
    result.budget, result.budget_flex = _parse_budget(raw_text)

    # 5. Color extraction
    result.color, result.color_family = _extract_color(raw_text)

    # 6. Location extraction
    result.location = _extract_location(raw_text)

    # 7. Urgency extraction
    result.urgency_days = _extract_urgency(raw_text)

    # 8. Smart default: if user gave location or color but no feel, inject a neutral feel
    if not result.feel and (result.location or result.color):
        result.feel = ["comfortable", "elegant"]

    # 9. Confidence + missing fields
    result.confidence, result.missing = _compute_confidence(result)

    # 10. Warnings
    if result.budget and result.budget < 300:
        result.warnings.append(
            f"Budget ₹{result.budget} is below minimum weaver pricing (₹300). "
            f"We may not find a match."
        )
    if result.budget and result.budget > 20000:
        result.warnings.append(
            f"Budget ₹{result.budget} is in premium range. "
            f"Lead times may be longer (21+ days)."
        )
    if result.confidence < 0.4:
        result.warnings.append(
            "Low confidence parse. Consider asking buyer for more details."
        )

    return result


def build_followup_question(missing: list[str]) -> str | None:
    """Generates a single follow-up question for the most important missing field."""
    priority = ["feel", "occasion", "budget", "color", "location"]
    for field in priority:
        if field in missing:
            questions = {
                "feel":     "How do you want the fabric to feel? (light and airy, rich and heavy, soft, flowy...)",
                "occasion": "What's the occasion? (wedding, festival, casual, office...)",
                "budget":   "What's your budget? (in rupees)",
                "color":    "Any color preference? (or say 'no preference')",
                "location": "Any specific weaving cluster or state you prefer? (e.g. Kanchipuram, Banaras, Kota...)",
            }
            return questions[field]
    return None


# ===========================================================================
# 10. TEST HARNESS – run to see the new capabilities
# ===========================================================================
if __name__ == "__main__":
    test_inputs = [
        # Devanagari – heavy, Kanchipuram
        "मुझे एक पीले रंग की कांचीपुरम साड़ी चाहिए",
        "कांचीपुरम सिल्क साठी चाहिए भारी",
        "शादी के लिए भारी रेशमी साड़ी, ₹1500 से कम",
        "हल्की सूती साड़ी ऑफिस के लिए, 800 रुपये",
        "मुझे बनारसी साड़ी चाहिए, रिसेप्शन के लिए, 5000 के आसपास",
        "पूजा के लिए एक शाही साड़ी, राजस्थान से, 2000 की बजट",
        "कच्छ की कॉटन साड़ी, रोज़ाना पहनने के लिए, 600 रु",
        # English / romanised
        "Kanchipuram silk saree for wedding, under ₹5000",
        "Light cotton saree for office, ₹700",
        "Banarasi saree for reception, around 8000",
        "Heavy royal silk for wedding, deep red, grand",
    ]

    print("=" * 70)
    print("PAKSHI INTENT PARSER — DEVANAGARI ENHANCED")
    print("=" * 70)

    for i, txt in enumerate(test_inputs, 1):
        res = parse_intent(txt)
        print(f"\n[{i:02d}] INPUT : {txt}")
        print(f"      LANG   : {res.language_hint}")
        print(f"      FEEL   : {res.feel}")
        print(f"      OCC    : {res.occasion}")
        print(f"      BUDGET : ₹{res.budget}" + (" (flexible)" if res.budget_flex else ""))
        print(f"      COLOR  : {res.color} ({res.color_family})")
        print(f"      LOC    : {res.location}")
        print(f"      URGENCY: {res.urgency_days} days" if res.urgency_days else "      URGENCY: not specified")
        print(f"      CONF   : {res.confidence:.0%}")
        if res.missing:
            followup = build_followup_question(res.missing)
            print(f"      FOLLOWUP → \"{followup}\"")
        if res.warnings:
            print(f"      WARN   : {res.warnings[0]}")
