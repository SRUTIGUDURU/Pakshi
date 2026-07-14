"""
Pakshi - ChromaDB Setup Script
Loads fabric swatches into ChromaDB
"""

import json
import numpy as np
import chromadb
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

BASE_DIR = Path(__file__).parent
CHROMA_DIR = BASE_DIR / "chroma_db"

# ---------------------------------------------------------------------------
# Custom TF-IDF embedding function that ChromaDB accepts
# ---------------------------------------------------------------------------
class TFIDFEmbeddingFunction:
    """
    ChromaDB-compatible embedding function using TF-IDF.
    Must implement __call__, embed_documents, and embed_query.
    Vectorizer is fitted on the full corpus at init time and reused for queries.
    """
    def __init__(self, documents: list[str]):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        self.vectorizer.fit(documents)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        matrix = self.vectorizer.transform(texts).toarray()
        normed = normalize(matrix, norm="l2")
        return normed.tolist()

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self._embed(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self._embed(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self._embed(input)


def build_searchable_text(swatch: dict) -> str:
    """
    Converts swatch fields into a natural language string for embedding.
    More overlap with buyer language = better semantic retrieval.
    """
    fabric = swatch["fabric_type"].replace("_", " ")
    sensory = " ".join(swatch["sensory_tags"])
    occasions = " ".join(swatch["occasion_tags"])
    return (
        f"{fabric} fabric {swatch['weave_style']} "
        f"color {swatch['color']} {swatch['color_family']} "
        f"{sensory} {occasions}"
    )


def load_swatches_into_chroma():
    with open(BASE_DIR / "fabric_swatches.json") as f:
        swatch_data = json.load(f)
    with open(BASE_DIR / "weaver_profiles.json") as f:
        weaver_data = json.load(f)

    weaver_lookup = {w["id"]: w for w in weaver_data["weaver_profiles"]}
    swatches = swatch_data["fabric_swatches"]

    # Build all documents first so vectorizer fits on the full corpus
    documents = [build_searchable_text(s) for s in swatches]
    ef = TFIDFEmbeddingFunction(documents)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection("fabric_swatches")
    except Exception:
        pass

    collection = client.create_collection(
        name="fabric_swatches",
        embedding_function=ef,
        metadata={"description": "Pakshi swatch catalog"}
    )

    ids, metadatas = [], []
    for swatch in swatches:
        weaver = weaver_lookup.get(swatch["weaver_id"], {})
        ids.append(swatch["id"])
        metadatas.append({
            "swatch_id":      swatch["id"],
            "weaver_id":      swatch["weaver_id"],
            "weaver_name":    weaver.get("name", "Unknown"),
            "weaver_cluster": weaver.get("cluster", "Unknown"),
            "weaver_state":   weaver.get("state", "Unknown"),
            "weaver_language":weaver.get("language", "Unknown"),
            "weaver_rating":  float(weaver.get("rating", 0.0)),
            "fabric_type":    swatch["fabric_type"],
            "weave_style":    swatch["weave_style"],
            "color":          swatch["color"],
            "color_family":   swatch["color_family"],
            "price_inr":      int(swatch["price_inr"]),
            "delivery_days":  int(swatch["delivery_days"]),
            "available":      swatch["available"],
            "occasion_tags":  ",".join(swatch["occasion_tags"]),
            "sensory_tags":   ",".join(swatch["sensory_tags"]),
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"✅ {len(ids)} swatches loaded into ChromaDB at {CHROMA_DIR}")
    return collection, ef


if __name__ == "__main__":
    col, _ = load_swatches_into_chroma()
    print(f"Collection count: {col.count()}")
