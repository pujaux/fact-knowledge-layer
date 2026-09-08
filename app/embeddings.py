"""Local, free embeddings used to find candidate matching facts across
documents BEFORE we spend any Groq tokens. This is what keeps the relationship
step cheap: instead of comparing every fact to every other fact with the LLM
(O(n^2) calls), we only ask Groq about pairs that already look similar."""

import numpy as np
from sentence_transformers import SentenceTransformer

_model = None


def get_model():
    global _model
    if _model is None:
        # small, fast, runs on CPU, ~80MB download the first time
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_facts(facts: list) -> np.ndarray:
    """facts: list of dicts with entity/metric/value/period/scope fields."""
    texts = [
        f"{f['entity']} | {f['metric']} | {f['value']} {f.get('unit') or ''} | "
        f"{f.get('period') or ''} | {f.get('scope') or ''}"
        for f in facts
    ]
    model = get_model()
    return model.encode(texts, normalize_embeddings=True)


def top_k_candidate_pairs(facts: list, embeddings: np.ndarray, k: int, threshold: float):
    """Returns list of (i, j, similarity) for i < j, only crossing documents,
    restricted to each fact's top-k nearest neighbors above threshold."""
    sims = embeddings @ embeddings.T
    pairs = set()
    n = len(facts)
    for i in range(n):
        neighbor_idx = np.argsort(-sims[i])
        count = 0
        for j in neighbor_idx:
            if j == i:
                continue
            if facts[j]["doc_id"] == facts[i]["doc_id"]:
                continue  # only cross-document comparisons -- that's the assignment's focus
            if sims[i][j] < threshold:
                break  # sorted descending, nothing further will pass
            key = (min(i, j), max(i, j))
            if key not in pairs:
                pairs.add(key)
                count += 1
            if count >= k:
                break
    return [(i, j, float(sims[i][j])) for i, j in pairs]
