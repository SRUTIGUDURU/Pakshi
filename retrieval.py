"""
Pakshi - RAG Retrieval Module
Given a parsed buyer intent dict, retrieves the top 3 matching swatches
from ChromaDB, applies budget filtering, and returns ranked results.
If no match within budget, triggers fallback logic from fabric_ontology.json.

Supports location filtering — if the buyer specifies a region (e.g., "Kanchipuram"),
only swatches from that region are returned.
"""

import json
from pathlib import Path
from setup_chromadb import load_swatches_into_chroma, TFIDFEmbeddingFunction

BASE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Load both ontology and full swatch catalog ONCE at module load
# ---------------------------------------------------------------------------
def _load_swatch_catalog():
    """Load the complete fabric_swatches.json and create a lookup by swatch_id."""
    with open(BASE_DIR / "fabric_swatches.json") as f:
        data = json.load(f)
    return {swatch["id"]: swatch for swatch in data["fabric_swatches"]}

_SWATCH_CATALOG = _load_swatch_catalog()


def load_ontology():
    with open(BASE_DIR / "fabric_ontology.json") as f:
        return json.load(f)


def build_query_text(intent: dict) -> str:
    """
    Converts parsed buyer intent into a query string that mirrors
    the swatch document format, maximising TF-IDF overlap.

    intent keys expected (from IntentResult.to_dict()):
      - feel      : list[str]  e.g. ["light", "airy"]
      - occasion  : str        e.g. "wedding"
      - budget    : int        e.g. 1500
      - color     : str|None   e.g. "green"
      - location  : str|None   e.g. "Kanchipuram"
    """
    feel = intent.get("feel") or []
    occ = intent.get("occasion") or ""
    color = intent.get("color") or ""
    location = intent.get("location") or ""

    # Build parts list, filtering out None and empty strings
    parts = feel + [occ, color, location]
    parts = [p for p in parts if p and isinstance(p, str)]
    return " ".join(parts)


def get_fallback(fabric_type: str, budget: int, ontology: dict) -> dict | None:
    """Returns fallback rule if budget is below minimum for fabric_type."""
    for rule in ontology["budget_fallback_rules"]:
        if (rule["requested_fabric"] == fabric_type and
                budget < rule["budget_too_low_below"]):
            return rule
    return None


def _matches_location(meta: dict, requested_location: str | None) -> bool:
    """
    Check if a swatch's weaver matches the requested location.
    Matches against both weaver_cluster and weaver_state.
    """
    if not requested_location:
        return True

    location_lower = requested_location.lower()

    # Check cluster (e.g., "Kanchipuram", "Pochampally")
    cluster = meta.get("weaver_cluster", "").lower()
    if location_lower in cluster or cluster in location_lower:
        return True

    # Check state (e.g., "Tamil Nadu", "Telangana")
    state = meta.get("weaver_state", "").lower()
    if location_lower in state or state in location_lower:
        return True

    return False


def _get_swatch_details(swatch_id: str) -> dict:
    """
    Look up rich text/visual details from the original JSON file.
    Returns a dict with description, image_url, and reviews.
    """
    swatch = _SWATCH_CATALOG.get(swatch_id, {})
    return {
        "description": swatch.get("description", "Handwoven by skilled artisans."),
        "image_url": swatch.get("image_url", ""),
        "reviews": swatch.get("reviews", []),
    }


def retrieve_swatches(intent: dict, top_k: int = 3) -> dict:
    """
    Main retrieval function.

    Returns:
      {
        "status": "match" | "fallback" | "no_match",
        "results": [...],          # top swatches if match
        "fallback": {...} | None,  # fallback rule if triggered
        "agent_message": str       # message to show buyer
      }
    """
    ontology = load_ontology()
    collection, ef = load_swatches_into_chroma()

    budget = intent.get("budget", 99999)
    location = intent.get("location")  # may be None
    query_text = build_query_text(intent)

    # Step 1 — semantic search over full collection (retrieve more, filter after)
    try:
        raw_results = collection.query(
            query_texts=[query_text],
            n_results=min(20, collection.count()),
        )
    except Exception as e:
        # If query fails (e.g., no documents), return no_match
        return {
            "status": "no_match",
            "results": [],
            "fallback": None,
            "agent_message": f"Search error: {e}. Please try a different description."
        }

    candidates = []
    for i, meta in enumerate(raw_results["metadatas"][0]):
        candidates.append({
            "meta": meta,
            "distance": raw_results["distances"][0][i],
            "document": raw_results["documents"][0][i],
        })

    # Step 2 — filter by budget, availability, AND location
    filtered = [
        c for c in candidates
        if (c["meta"]["price_inr"] <= budget
            and c["meta"]["available"]
            and _matches_location(c["meta"], location))
    ]

    # Step 3 — if we have matches, rank by distance then weaver rating
    if filtered:
        ranked = sorted(
            filtered,
            key=lambda x: (x["distance"], -x["meta"]["weaver_rating"])
        )[:top_k]

        results = []
        for r in ranked:
            m = r["meta"]
            swatch_id = m["swatch_id"]
            details = _get_swatch_details(swatch_id)

            # Safely parse sensory_tags and occasion_tags (they might be None)
            sensory_tags = m.get("sensory_tags")
            if sensory_tags is None:
                sensory_tags = ""
            if not isinstance(sensory_tags, str):
                sensory_tags = ""
            sensory_list = [t.strip() for t in sensory_tags.split(",") if t.strip()]

            occasion_tags = m.get("occasion_tags")
            if occasion_tags is None:
                occasion_tags = ""
            if not isinstance(occasion_tags, str):
                occasion_tags = ""
            occasion_list = [t.strip() for t in occasion_tags.split(",") if t.strip()]

            results.append({
                "swatch_id":      swatch_id,
                "fabric_type":    m["fabric_type"],
                "weave_style":    m["weave_style"],
                "color":          m["color"],
                "price_inr":      m["price_inr"],
                "delivery_days":  m["delivery_days"],
                "weaver_name":    m["weaver_name"],
                "weaver_cluster": m["weaver_cluster"],
                "weaver_state":   m["weaver_state"],
                "weaver_rating":  m["weaver_rating"],
                "sensory_tags":   sensory_list,
                "occasion_tags":  occasion_list,
                "description":    details["description"],
                "image_url":      details["image_url"],
                "reviews":        details["reviews"],
            })

        location_msg = f" in {location}" if location else ""
        return {
            "status": "match",
            "results": results,
            "fallback": None,
            "agent_message": (
                f"Found {len(results)} matching swatches{location_msg} within ₹{budget}. "
                f"Please select one to proceed."
            )
        }

    # Step 4 — no match within budget, check ontology for fallback
    feel_tags = intent.get("feel", [])
    sensory_map = ontology["sensory_to_fabric_mapping"]
    fabric_votes: dict[str, int] = {}
    for tag in feel_tags:
        if tag in sensory_map:
            for fabric in sensory_map[tag]:
                fabric_votes[fabric] = fabric_votes.get(fabric, 0) + 1

    intended_fabric = max(fabric_votes, key=fabric_votes.get) if fabric_votes else "cotton"
    fallback_rule = get_fallback(intended_fabric, budget, ontology)

    if fallback_rule and fallback_rule["fallback_fabric"]:
        fallback_fabric = fallback_rule["fallback_fabric"]

        # Retrieve swatches for the fallback fabric within a relaxed budget
        relaxed_budget = budget + 800
        fallback_candidates = [
            c for c in candidates
            if (c["meta"]["fabric_type"] == fallback_fabric
                and c["meta"]["price_inr"] <= relaxed_budget
                and c["meta"]["available"]
                and _matches_location(c["meta"], location))
        ]
        fallback_results = sorted(
            fallback_candidates,
            key=lambda x: (x["distance"], -x["meta"]["weaver_rating"])
        )[:top_k]

        fallback_swatches = []
        for r in fallback_results:
            m = r["meta"]
            swatch_id = m["swatch_id"]
            details = _get_swatch_details(swatch_id)

            sensory_tags = m.get("sensory_tags")
            if sensory_tags is None:
                sensory_tags = ""
            if not isinstance(sensory_tags, str):
                sensory_tags = ""
            sensory_list = [t.strip() for t in sensory_tags.split(",") if t.strip()]

            occasion_tags = m.get("occasion_tags")
            if occasion_tags is None:
                occasion_tags = ""
            if not isinstance(occasion_tags, str):
                occasion_tags = ""
            occasion_list = [t.strip() for t in occasion_tags.split(",") if t.strip()]

            fallback_swatches.append({
                "swatch_id":      swatch_id,
                "fabric_type":    m["fabric_type"],
                "weave_style":    m["weave_style"],
                "color":          m["color"],
                "price_inr":      m["price_inr"],
                "delivery_days":  m["delivery_days"],
                "weaver_name":    m["weaver_name"],
                "weaver_cluster": m["weaver_cluster"],
                "weaver_state":   m["weaver_state"],
                "weaver_rating":  m["weaver_rating"],
                "sensory_tags":   sensory_list,
                "occasion_tags":  occasion_list,
                "description":    details["description"],
                "image_url":      details["image_url"],
                "reviews":        details["reviews"],
            })

        location_msg = f" in {location}" if location else ""
        agent_msg = (
            f"No {intended_fabric.replace('_',' ')} match found{location_msg} within ₹{budget}. "
            f"{fallback_rule['message']} "
            f"Say YES to see {fallback_fabric.replace('_',' ')} options "
            f"or NO to wait for ₹{budget} availability."
        )

        return {
            "status": "fallback",
            "results": fallback_swatches,
            "fallback": fallback_rule,
            "agent_message": agent_msg
        }

    # Step 5 — truly no match
    location_msg = f" in {location}" if location else ""
    return {
        "status": "no_match",
        "results": [],
        "fallback": None,
        "agent_message": (
            f"No swatches found{location_msg} within ₹{budget}. "
            f"We'll notify you when a matching weaver becomes available."
        )
    }
