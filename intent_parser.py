"""
Pakshi — Intent Parser
=======================
Converts raw buyer text (any Indian language, romanised, or English)
into a structured intent dict consumed by retrieval.py.

Pipeline:
  raw text → language detection → keyword normalisation
           → feel extraction → occasion mapping → budget extraction
           → color extraction → urgency detection → confidence scoring
           → structured IntentResult

Supports:
  - English, Hinglish, romanised Telugu/Tamil/Kannada/Bengali
  - Budget expressions: "1500 rupees", "₹1500", "1.5k", "under 2000",
    "around 800", "1500 se kam", "below 2k"
  - Occasion aliases: "shaadi", "kalyanam", "pellikuturu", "biye",
    "casual", "office", "college", etc.
  - Urgency: "within a week", "urgent", "jaldi", "next month"
  - Color hints: "deep red", "pastel", "earth tones", "light colours"
  - Confidence score so the agent knows when to ask a follow-up
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


# ---------------------------------------------------------------------------
# Occasion aliases  (alias → canonical occasion tag)
# ---------------------------------------------------------------------------
OCCASION_ALIASES: dict[str, str] = {
    # Wedding
    "wedding":          "wedding",
    "shaadi":           "wedding",
    "shadi":            "wedding",
    "kalyanam":         "wedding",
    "pellikuturu":      "wedding",
    "vivah":            "wedding",
    "biye":             "wedding",
    "lagna":            "wedding",
    "marriage":         "wedding",
    "nikah":            "wedding",
    "reception":        "reception",
    "engagement":       "reception",
    "roka":             "reception",

    # Festival
    "festival":         "festival",
    "puja":             "festival",
    "pooja":            "festival",
    "navratri":         "festival",
    "dussehra":         "festival",
    "diwali":           "festival",
    "onam":             "festival",
    "pongal":           "festival",
    "ugadi":            "festival",
    "sankranti":        "festival",
    "eid":              "festival",
    "durga puja":       "festival",
    "ganesh chaturthi": "festival",
    "holi":             "festival",

    # Casual / Daily
    "casual":           "casual",
    "daily":            "daily_wear",
    "daily wear":       "daily_wear",
    "everyday":         "daily_wear",
    "regular":          "daily_wear",
    "roz ka":           "daily_wear",
    "rozana":           "daily_wear",
    "normal":           "daily_wear",

    # Work / Office
    "office":           "work",
    "work":             "work",
    "professional":     "work",
    "formal":           "formal",
    "meeting":          "work",
    "conference":       "work",

    # College / Young
    "college":          "college",
    "university":       "college",
    "campus":           "college",
    "class":            "college",

    # Summer
    "summer":           "summer",
    "summer wedding":   "summer_wedding",
    "beach":            "summer",
    "grishma":          "summer",

    # Semi-formal
    "semi formal":      "semi_formal",
    "semi-formal":      "semi_formal",
    "party":            "semi_formal",
    "get together":     "semi_formal",

    # Ceremony
    "ceremony":         "ceremony",
    "gruhapravesam":    "ceremony",
    "housewarming":     "ceremony",
    "baby shower":      "ceremony",
    "seemantham":       "ceremony",
}


# ---------------------------------------------------------------------------
# Feel / sensory keyword map  (keyword → list of feel tags)
# ---------------------------------------------------------------------------
FEEL_KEYWORDS: dict[str, list[str]] = {
    # Lightness
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

    # Softness / comfort
    "soft":             ["soft", "comfortable"],
    "naram":            ["soft"],
    "comfortable":      ["comfortable"],
    "comfortable fabric":["comfortable"],
    "easy":             ["comfortable", "everyday"],
    "cozy":             ["comfortable", "soft"],

    # Richness / formality
    "rich":             ["rich", "elegant"],
    "luxurious":        ["luxurious", "rich"],
    "luxury":           ["luxurious", "rich"],
    "grand":            ["grand", "royal"],
    "royal":            ["royal", "grand"],
    "shahi":            ["royal", "grand"],
    "elegant":          ["elegant"],
    "classy":           ["elegant", "rich"],
    "graceful":         ["elegant", "flowy"],

    # Sheen / finish
    "shiny":            ["glossy", "shiny"],
    "glossy":           ["glossy"],
    "matte":            ["matte"],
    "shimmer":          ["glossy", "shiny"],
    "glitter":          ["glossy"],
    "dull":             ["matte"],

    # Weight
    "heavy":            ["heavy", "stiff"],
    "bhaari":           ["heavy"],
    "stiff":            ["stiff"],
    "structured":       ["stiff", "structured"],
    "thick":            ["heavy"],

    # Occasion-derived feel
    "wedding fabric":   ["elegant", "rich"],
    "bridal":           ["luxurious", "rich", "royal"],
    "party wear":       ["elegant", "semi-formal"],
    "traditional":      ["traditional"],
    "ethnic":           ["traditional"],
    "desi":             ["traditional"],
    "fusion":           ["versatile"],
    "modern":           ["versatile"],
    "indo western":     ["versatile"],

    # Sensory metaphors buyers actually use
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


# ---------------------------------------------------------------------------
# Color keyword map  (keyword → (display_name, color_family))
# ---------------------------------------------------------------------------
COLOR_KEYWORDS: dict[str, tuple[str, str]] = {
    # Reds
    "red":          ("red", "red"),
    "dark red":     ("dark red", "red"),
    "deep red":     ("deep red", "red"),
    "maroon":       ("maroon", "red"),
    "burgundy":     ("maroon", "red"),
    "wine":         ("wine red", "red"),
    "crimson":      ("crimson", "red"),
    "vermillion":   ("vermillion red", "red"),
    "laal":         ("red", "red"),
    "surkh":        ("red", "red"),

    # Pinks
    "pink":         ("pink", "pink"),
    "light pink":   ("pale pink", "pink"),
    "pale pink":    ("pale pink", "pink"),
    "dusty rose":   ("dusty rose", "pink"),
    "rose":         ("dusty rose", "pink"),
    "blush":        ("pale pink", "pink"),
    "magenta":      ("magenta", "pink"),
    "hot pink":     ("magenta", "pink"),
    "coral":        ("coral", "pink"),
    "gulaabi":      ("pink", "pink"),

    # Oranges
    "orange":       ("orange", "orange"),
    "saffron":      ("saffron", "orange"),
    "kesari":       ("saffron", "orange"),
    "peach":        ("peach", "orange"),
    "rust":         ("rust", "orange"),
    "terracotta":   ("rust", "orange"),

    # Yellows
    "yellow":       ("yellow", "yellow"),
    "mustard":      ("mustard yellow", "yellow"),
    "golden":       ("soft gold", "yellow"),
    "gold":         ("soft gold", "yellow"),
    "pale gold":    ("pale gold", "yellow"),
    "champagne":    ("champagne", "yellow"),
    "ivory":        ("ivory", "neutral"),
    "pila":         ("yellow", "yellow"),

    # Greens
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
    "hara":         ("green", "green"),
    "mehendi":      ("dark green", "green"),

    # Blues
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
    "neela":        ("blue", "blue"),

    # Purples
    "purple":       ("purple", "purple"),
    "violet":       ("purple", "purple"),
    "lavender":     ("lavender", "purple"),
    "lilac":        ("lilac", "purple"),
    "deep purple":  ("deep purple", "purple"),
    "plum":         ("deep purple", "purple"),
    "mauve":        ("lilac", "purple"),
    "baingani":     ("purple", "purple"),

    # Neutrals
    "white":        ("white", "neutral"),
    "cream":        ("cream", "neutral"),
    "off white":    ("off-white", "neutral"),
    "off-white":    ("off-white", "neutral"),
    "beige":        ("beige", "neutral"),
    "nude":         ("beige", "neutral"),
    "natural":      ("natural beige", "neutral"),
    "brown":        ("natural beige", "neutral"),
    "black":        ("black", "neutral"),
    "grey":         ("grey", "neutral"),
    "gray":         ("grey", "neutral"),
    "safed":        ("white", "neutral"),
    "kala":         ("black", "neutral"),

    # Vague / descriptive
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


# ---------------------------------------------------------------------------
# Urgency patterns
# ---------------------------------------------------------------------------
URGENCY_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"today|abhi|aaj",           re.I), 1),
    (re.compile(r"tomor",                    re.I), 2),
    (re.compile(r"2\s*days?|do\s*din",       re.I), 2),
    (re.compile(r"3\s*days?|teen\s*din",     re.I), 3),
    (re.compile(r"this\s*week|is\s*hafte",   re.I), 5),
    (re.compile(r"week|hafte",               re.I), 7),
    (re.compile(r"10\s*days?",               re.I), 10),
    (re.compile(r"2\s*weeks?|do\s*hafte",    re.I), 14),
    (re.compile(r"next\s*month|agle\s*mahine",re.I), 30),
    (re.compile(r"month|mahine",             re.I), 30),
    (re.compile(r"no\s*rush|anytime",        re.I), 90),
]


# ---------------------------------------------------------------------------
# Budget patterns — covers Indian English + Hindi expressions
# ---------------------------------------------------------------------------
def _parse_budget(text: str) -> tuple[int | None, bool]:
    """
    Returns (budget_inr, is_flexible).
    is_flexible = True when phrasing suggests "around/approx/under".
    """
    text = text.lower().replace(",", "")

    flex_words = re.compile(
        r"\b(around|approx|approximately|about|roughly|nearly|"
        r"lagbhag|lagbhag|kaafi|under|below|less than|se kam|tak|upto|up to)\b",
        re.I
    )
    is_flexible = bool(flex_words.search(text))

    # Patterns ranked by specificity
    patterns = [
        # ₹1,500 or Rs 1500
        (r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s*k",    1000),
        (r"(?:₹|rs\.?|inr)\s*(\d[\d,]*)",              1),
        # "1.5k" or "2k"
        (r"(\d+(?:\.\d+)?)\s*k(?:rupee|rupees?)?",      1000),
        # "1500 rupees" or "1500 rs"
        (r"(\d[\d,]*)\s*(?:rupees?|rs\.?|inr)",         1),
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


# ---------------------------------------------------------------------------
# Language detection (lightweight heuristic — no external model needed)
# ---------------------------------------------------------------------------
_HINDI_MARKERS   = {"hai", "ka", "ki", "ke", "mein", "se", "koi", "bahut",
                    "acha", "thoda", "shaadi", "kapda", "lena", "chahiye",
                    "rupaye", "halka", "bhaari", "naram"}
_TELUGU_MARKERS  = {"kalyanam", "pellikuturu", "saree", "chali", "manchidi"}
_TAMIL_MARKERS   = {"kalyanam", "pudavai", "nalla", "romba", "saree"}
_BENGALI_MARKERS = {"biye", "saree", "khoob", "sundor", "bhalo"}


def _detect_language(text: str) -> str:
    words = set(text.lower().split())
    if words & _HINDI_MARKERS:
        return "hinglish"
    if words & _TELUGU_MARKERS:
        return "romanised_telugu"
    if words & _TAMIL_MARKERS:
        return "romanised_tamil"
    if words & _BENGALI_MARKERS:
        return "romanised_bengali"
    return "english"


# ---------------------------------------------------------------------------
# Core parsing functions
# ---------------------------------------------------------------------------

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

    # Multi-word phrases first
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


def _extract_urgency(text: str) -> int | None:
    """Returns max acceptable delivery days or None."""
    for pattern, days in URGENCY_PATTERNS:
        if pattern.search(text):
            return days
    return None


def _compute_confidence(result: IntentResult) -> tuple[float, list[str]]:
    """
    Returns (confidence_score, list_of_missing_fields).
    Scoring: feel=40pts, occasion=30pts, budget=20pts, color=10pts
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
        score += 0.10
    else:
        missing.append("color")

    return round(score, 2), missing


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_intent(raw_text: str) -> IntentResult:
    """
    Main entry point. Takes raw buyer text and returns IntentResult.

    Usage:
        result = parse_intent("Light saree for summer wedding, budget ₹1500")
        print(result.to_dict())
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

    # 6. Urgency extraction
    result.urgency_days = _extract_urgency(raw_text)

    # 7. Confidence + missing fields
    result.confidence, result.missing = _compute_confidence(result)

    # 8. Warnings
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
    priority = ["feel", "occasion", "budget", "color"]
    for field in priority:
        if field in missing:
            questions = {
                "feel":     "How do you want the fabric to feel? (light and airy, rich and heavy, soft, flowy...)",
                "occasion": "What's the occasion? (wedding, festival, casual, office...)",
                "budget":   "What's your budget? (in rupees)",
                "color":    "Any color preference? (or say 'no preference')",
            }
            return questions[field]
    return None


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_inputs = [
        # English — standard
        "I want a light airy saree for a summer wedding, budget ₹1500, preferably in green",
        # Hinglish
        "Shaadi ke liye kuch flowy chahiye, around 2000 rupaye, light colour",
        # Very vague
        "something nice for a function",
        # Budget only
        "saree under 800",
        # Romanised Telugu
        "Pellikuturu ki cotton silk saree, 3000 ke andar, pastel colours",
        # Over-detailed
        "I need a royal silk saree for my sister's wedding reception next month, "
        "deep red or maroon, budget is around ₹8000, it should be heavy and grand",
        # Low budget trigger
        "casual cotton saree, very cheap, 200 rupees only",
        # Urgency
        "need a saree for office within this week, breathable cotton, under 1000",
        # Color-heavy
        "mustard yellow flowy saree for Diwali, around 1500",
        # Multi-word occasion
        "something for durga puja, soft and comfortable, 1200 budget",
        # Very high budget
        "Kanjivaram silk for wedding, ₹15000, deep green with gold border",
        # Romanised Bengali
        "biye te porer jonno ekta sundor saree, 3000 takar modhye, light colour",
    ]

    print("=" * 70)
    print("PAKSHI INTENT PARSER — TEST RUNS")
    print("=" * 70)

    for i, text in enumerate(test_inputs, 1):
        result = parse_intent(text)
        print(f"\n[{i:02d}] INPUT : {text}")
        print(f"      LANG   : {result.language_hint}")
        print(f"      FEEL   : {result.feel}")
        print(f"      OCC    : {result.occasion}")
        print(f"      BUDGET : ₹{result.budget}" +
              (" (flexible)" if result.budget_flex else "") +
              (" — " + str(result.warnings[0]) if result.warnings else ""))
        print(f"      COLOR  : {result.color} ({result.color_family})")
        print(f"      URGENCY: {result.urgency_days} days" if result.urgency_days else
              f"      URGENCY: not specified")
        print(f"      CONF   : {result.confidence:.0%}")
        if result.missing:
            followup = build_followup_question(result.missing)
            print(f"      FOLLOWUP → \"{followup}\"")
        print()
