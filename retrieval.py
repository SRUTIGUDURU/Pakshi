"""
Pakshi - RAG Retrieval Module (Location‑Aware & Safe)
"""
import json
from pathlib import Path
from setup_chromadb import load_swatches_into_chroma

BASE_DIR = Path(__file__).parent

def _load_swatch_catalog():
    with open(BASE_DIR / "fabric_swatches.json") as f:
        data = json.load(f)
    return {swatch["id"]: swatch for swatch in data["fabric_swatches"]}
_SWATCH_CATALOG = _load_swatch_catalog()

def load_ontology():
    with open(BASE_DIR / "fabric_ontology.json") as f:
        return json.load(f)

def build_query_text(intent: dict) -> str:
    feel = intent.get("feel") or []
    occ = intent.get("occasion") or ""
    color = intent.get("color") or ""
    location = intent.get("location") or ""
    parts = feel + [occ, color, location]
    parts = [p for p in parts if p and isinstance(p, str)]
    return " ".join(parts)

def get_fallback(fabric_type: str, budget: int, ontology: dict):
    for rule in ontology["budget_fallback_rules"]:
        if rule["requested_fabric"] == fabric_type and budget < rule["budget_too_low_below"]:
            return rule
    return None

def _matches_location(meta: dict, requested_location: str | None) -> bool:
    if not requested_location:
        return True
    loc_lower = requested_location.lower()
    cluster = meta.get("weaver_cluster", "").lower()
    state = meta.get("weaver_state", "").lower()
    return (loc_lower in cluster or cluster in loc_lower or
            loc_lower in state or state in loc_lower)

def _get_swatch_details(swatch_id: str) -> dict:
    swatch = _SWATCH_CATALOG.get(swatch_id, {})
    return {
        "description": swatch.get("description", "Handwoven by skilled artisans."),
        "image_url": swatch.get("image_url", ""),
        "reviews": swatch.get("reviews", []),
    }

def retrieve_swatches(intent: dict, top_k: int = 3) -> dict:
    ontology = load_ontology()
    collection, ef = load_swatches_into_chroma()

    budget = intent.get("budget", 99999)
    location = intent.get("location")
    query_text = build_query_text(intent)

    if not query_text.strip():
        # If query is empty, return no_match
        return {
            "status": "no_match",
            "results": [],
            "fallback": None,
            "agent_message": "Please describe what you're looking for (e.g. fabric, colour, occasion)."
        }

    try:
        raw_results = collection.query(
            query_texts=[query_text],
            n_results=min(20, collection.count()),
        )
    except Exception as e:
        return {
            "status": "no_match",
            "results": [],
            "fallback": None,
            "agent_message": f"Search error: {e}"
        }

    candidates = []
    for i, meta in enumerate(raw_results["metadatas"][0]):
        candidates.append({
            "meta": meta,
            "distance": raw_results["distances"][0][i],
            "document": raw_results["documents"][0][i],
        })

    filtered = [
        c for c in candidates
        if (c["meta"]["price_inr"] <= budget
            and c["meta"]["available"]
            and _matches_location(c["meta"], location))
    ]

    if filtered:
        ranked = sorted(filtered, key=lambda x: (x["distance"], -x["meta"]["weaver_rating"]))[:top_k]
        results = []
        for r in ranked:
            m = r["meta"]
            details = _get_swatch_details(m["swatch_id"])
            # Safe parse of tags
            sensory = m.get("sensory_tags")
            if not sensory or not isinstance(sensory, str):
                sensory = ""
            sensory_list = [t.strip() for t in sensory.split(",") if t.strip()]
            occasion = m.get("occasion_tags")
            if not occasion or not isinstance(occasion, str):
                occasion = ""
            occasion_list = [t.strip() for t in occasion.split(",") if t.strip()]

            results.append({
                "swatch_id": m["swatch_id"],
                "fabric_type": m["fabric_type"],
                "weave_style": m["weave_style"],
                "color": m["color"],
                "price_inr": m["price_inr"],
                "delivery_days": m["delivery_days"],
                "weaver_name": m["weaver_name"],
                "weaver_cluster": m["weaver_cluster"],
                "weaver_state": m["weaver_state"],
                "weaver_rating": m["weaver_rating"],
                "sensory_tags": sensory_list,
                "occasion_tags": occasion_list,
                "description": details["description"],
                "image_url": details["image_url"],
                "reviews": details["reviews"],
            })

        location_msg = f" in {location}" if location else ""
        return {
            "status": "match",
            "results": results,
            "fallback": None,
            "agent_message": f"Found {len(results)} matching swatches{location_msg} within ₹{budget}."
        }

    # Fallback
    feel_tags = intent.get("feel", [])
    sensory_map = ontology["sensory_to_fabric_mapping"]
    fabric_votes = {}
    for tag in feel_tags:
        if tag in sensory_map:
            for fab in sensory_map[tag]:
                fabric_votes[fab] = fabric_votes.get(fab, 0) + 1
    intended_fabric = max(fabric_votes, key=fabric_votes.get) if fabric_votes else "cotton"
    fallback_rule = get_fallback(intended_fabric, budget, ontology)

    if fallback_rule and fallback_rule["fallback_fabric"]:
        fallback_fabric = fallback_rule["fallback_fabric"]
        relaxed_budget = budget + 800
        fallback_candidates = [
            c for c in candidates
            if (c["meta"]["fabric_type"] == fallback_fabric
                and c["meta"]["price_inr"] <= relaxed_budget
                and c["meta"]["available"]
                and _matches_location(c["meta"], location))
        ]
        fallback_results = sorted(fallback_candidates,
            key=lambda x: (x["distance"], -x["meta"]["weaver_rating"]))[:top_k]
        fallback_swatches = []
        for r in fallback_results:
            m = r["meta"]
            details = _get_swatch_details(m["swatch_id"])
            sensory = m.get("sensory_tags")
            if not sensory or not isinstance(sensory, str):
                sensory = ""
            sensory_list = [t.strip() for t in sensory.split(",") if t.strip()]
            occasion = m.get("occasion_tags")
            if not occasion or not isinstance(occasion, str):
                occasion = ""
            occasion_list = [t.strip() for t in occasion.split(",") if t.strip()]
            fallback_swatches.append({
                "swatch_id": m["swatch_id"],
                "fabric_type": m["fabric_type"],
                "weave_style": m["weave_style"],
                "color": m["color"],
                "price_inr": m["price_inr"],
                "delivery_days": m["delivery_days"],
                "weaver_name": m["weaver_name"],
                "weaver_cluster": m["weaver_cluster"],
                "weaver_state": m["weaver_state"],
                "weaver_rating": m["weaver_rating"],
                "sensory_tags": sensory_list,
                "occasion_tags": occasion_list,
                "description": details["description"],
                "image_url": details["image_url"],
                "reviews": details["reviews"],
            })
        location_msg = f" in {location}" if location else ""
        return {
            "status": "fallback",
            "results": fallback_swatches,
            "fallback": fallback_rule,
            "agent_message": (
                f"No {intended_fabric.replace('_',' ')} match{location_msg} within ₹{budget}. "
                f"{fallback_rule['message']} Say YES to see {fallback_fabric.replace('_',' ')} options or NO to wait."
            )
        }

    location_msg = f" in {location}" if location else ""
    return {
        "status": "no_match",
        "results": [],
        "fallback": None,
        "agent_message": f"No swatches found{location_msg} within ₹{budget}. We'll notify you."
    }
