"""
Pakshi - RAG Retrieval Module
Given a parsed buyer intent dict, retrieves the top 3 matching swatches
from ChromaDB, applies budget filtering, and returns ranked results.
If no match within budget, triggers fallback logic from fabric_ontology.json.
"""

import json
from pathlib import Path
from setup_chromadb import load_swatches_into_chroma, TFIDFEmbeddingFunction

BASE_DIR = Path(__file__).parent


def load_ontology():
    with open(BASE_DIR / "fabric_ontology.json") as f:
        return json.load(f)


def build_query_text(intent: dict) -> str:
    """
    Converts parsed buyer intent into a query string that mirrors
    the swatch document format, maximising TF-IDF overlap.

    intent keys expected:
      - feel      : list[str]  e.g. ["light", "airy"]
      - occasion  : str        e.g. "wedding"
      - budget    : int        e.g. 1500
      - color     : str|None   e.g. "green" (optional)
    """
    parts = intent.get("feel", []) + [intent.get("occasion", "")]
    if intent.get("color"):
        parts.append(intent["color"])
    return " ".join(parts)


def get_fallback(fabric_type: str, budget: int, ontology: dict) -> dict | None:
    """Returns fallback rule if budget is below minimum for fabric_type."""
    for rule in ontology["budget_fallback_rules"]:
        if (rule["requested_fabric"] == fabric_type and
                budget < rule["budget_too_low_below"]):
            return rule
    return None


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
    occasion = intent.get("occasion", "")
    query_text = build_query_text(intent)

    # Step 1 — semantic search over full collection (retrieve more, filter after)
    raw_results = collection.query(
        query_texts=[query_text],
        n_results=min(20, collection.count()),
    )

    candidates = []
    for i, meta in enumerate(raw_results["metadatas"][0]):
        candidates.append({
            "meta": meta,
            "distance": raw_results["distances"][0][i],
            "document": raw_results["documents"][0][i],
        })

    # Step 2 — filter by budget and availability
    within_budget = [
        c for c in candidates
        if c["meta"]["price_inr"] <= budget and c["meta"]["available"]
    ]

    # Step 3 — if we have matches, rank by distance then weaver rating
    if within_budget:
        ranked = sorted(
            within_budget,
            key=lambda x: (x["distance"], -x["meta"]["weaver_rating"])
        )[:top_k]

        results = []
        for r in ranked:
            m = r["meta"]
            results.append({
                "swatch_id":      m["swatch_id"],
                "fabric_type":    m["fabric_type"],
                "weave_style":    m["weave_style"],
                "color":          m["color"],
                "price_inr":      m["price_inr"],
                "delivery_days":  m["delivery_days"],
                "weaver_name":    m["weaver_name"],
                "weaver_cluster": m["weaver_cluster"],
                "weaver_state":   m["weaver_state"],
                "weaver_rating":  m["weaver_rating"],
                "sensory_tags":   m["sensory_tags"].split(","),
                "occasion_tags":  m["occasion_tags"].split(","),
            })

        return {
            "status": "match",
            "results": results,
            "fallback": None,
            "agent_message": (
                f"Found {len(results)} matching swatches within ₹{budget}. "
                f"Please select one to proceed."
            )
        }

    # Step 4 — no match within budget, check ontology for fallback
    # Guess the intended fabric from feel tags
    feel_tags = intent.get("feel", [])
    sensory_map = ontology["sensory_to_fabric_mapping"]
    fabric_votes: dict[str, int] = {}
    for tag in feel_tags:
        for fabric in sensory_map.get(tag, []):
            fabric_votes[fabric] = fabric_votes.get(fabric, 0) + 1

    intended_fabric = max(fabric_votes, key=fabric_votes.get) if fabric_votes else "cotton"
    fallback_rule = get_fallback(intended_fabric, budget, ontology)

    if fallback_rule and fallback_rule["fallback_fabric"]:
        fallback_fabric = fallback_rule["fallback_fabric"]
        fallback_min = next(
            f["price_range_inr"]["min"]
            for f in ontology["fabrics"]
            if f["id"] == fallback_fabric
        )

        # Retrieve swatches for the fallback fabric within a relaxed budget
        relaxed_budget = budget + 800
        fallback_candidates = [
            c for c in candidates
            if (c["meta"]["fabric_type"] == fallback_fabric
                and c["meta"]["price_inr"] <= relaxed_budget
                and c["meta"]["available"])
        ]
        fallback_results = sorted(
            fallback_candidates,
            key=lambda x: (x["distance"], -x["meta"]["weaver_rating"])
        )[:top_k]

        fallback_swatches = []
        for r in fallback_results:
            m = r["meta"]
            fallback_swatches.append({
                "swatch_id":      m["swatch_id"],
                "fabric_type":    m["fabric_type"],
                "weave_style":    m["weave_style"],
                "color":          m["color"],
                "price_inr":      m["price_inr"],
                "delivery_days":  m["delivery_days"],
                "weaver_name":    m["weaver_name"],
                "weaver_cluster": m["weaver_cluster"],
                "weaver_state":   m["weaver_state"],
                "weaver_rating":  m["weaver_rating"],
                "sensory_tags":   m["sensory_tags"].split(","),
                "occasion_tags":  m["occasion_tags"].split(","),
            })

        agent_msg = (
            f"No {intended_fabric.replace('_',' ')} match found within ₹{budget}. "
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
    return {
        "status": "no_match",
        "results": [],
        "fallback": None,
        "agent_message": (
            f"No swatches found for your request within ₹{budget}. "
            f"We'll notify you when a matching weaver becomes available."
        )
    }


# ---------------------------------------------------------------------------
# Quick test harness
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        {
            "label": "Happy path — cotton, wedding, ₹1500",
            "intent": {
                "feel": ["light", "airy", "elegant"],
                "occasion": "wedding",
                "budget": 1500,
                "color": "green"
            }
        },
        {
            "label": "Budget fallback — silk requested but budget ₹1500",
            "intent": {
                "feel": ["rich", "royal", "glossy"],
                "occasion": "wedding",
                "budget": 1500,
                "color": None
            }
        },
        {
            "label": "Summer wedding — flowy, cotton-silk range",
            "intent": {
                "feel": ["flowy", "airy", "breathable yet elegant"],
                "occasion": "summer_wedding",
                "budget": 2000,
                "color": "pastel"
            }
        },
        {
            "label": "Casual daily wear — very low budget ₹400",
            "intent": {
                "feel": ["light", "soft", "everyday"],
                "occasion": "casual",
                "budget": 400,
                "color": None
            }
        },
    ]

    print("=" * 60)
    print("PAKSHI RAG RETRIEVAL — TEST RUNS")
    print("=" * 60)

    for case in test_cases:
        print(f"\n📌 {case['label']}")
        print(f"   Intent: {case['intent']}")
        result = retrieve_swatches(case["intent"])
        print(f"   Status: {result['status'].upper()}")
        print(f"   Agent:  {result['agent_message']}")
        if result["results"]:
            print(f"   Top matches:")
            for r in result["results"]:
                print(f"     → [{r['swatch_id']}] {r['fabric_type']} | "
                      f"{r['weave_style']} | {r['color']} | "
                      f"₹{r['price_inr']} | {r['weaver_name']} "
                      f"({r['weaver_cluster']}) ⭐{r['weaver_rating']}")
        print()
