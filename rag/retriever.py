"""Semantic retrieval (cosine similarity) over an in-memory index built from data/documents at startup."""
import threading
from typing import List, Optional

import numpy as np

from rag.embeddings import make_embedder
from rag.ingest import load_chunks
from utils import config


class Retriever:
    def __init__(self, docs_dir=None):
        self.records = load_chunks(docs_dir)
        if not self.records:
            raise RuntimeError(f"No documents found in {docs_dir or config.DOCS_DIR}")
        texts = [r["text"] for r in self.records]
        self.embedder = make_embedder().fit(texts)
        self.matrix = self.embedder.encode(texts)
        self._lower = [r["text"].lower() + " " + r["title"].lower() for r in self.records]

    def search(self, query: str, crop: str = "", k: Optional[int] = None,
               min_score: Optional[float] = None) -> List[dict]:
        k = k or config.TOP_K
        min_score = config.MIN_SCORE if min_score is None else min_score
        scores = self.matrix @ self.embedder.encode([query])[0]
        crop = (crop or "").strip().lower()
        if crop and crop != "other":  # small boost for chunks that talk about the farmer's crop
            scores = scores + np.array([0.06 if crop in t else 0.0 for t in self._lower])
        out = []
        for i in np.argsort(-scores)[:k]:
            if scores[i] >= min_score:
                r = dict(self.records[i])
                r["score"] = round(float(scores[i]), 3)
                out.append(r)
        return out


_lock = threading.Lock()
_instance: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _instance
    with _lock:
        if _instance is None:
            _instance = Retriever()
        return _instance
