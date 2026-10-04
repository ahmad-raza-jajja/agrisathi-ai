"""Embedding backends: tfidf (default, no downloads, works on Streamlit Cloud) or sentence-transformers."""
import numpy as np

from utils import config
from utils.logging import get_logger

log = get_logger("embeddings")


class TfidfEmbedder:
    name = "tfidf"

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")

    def fit(self, texts):
        self.vec.fit(texts)
        return self

    def encode(self, texts):
        return self.vec.transform(texts).toarray().astype("float32")


class STEmbedder:
    name = "st"

    def __init__(self, model_name):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def fit(self, texts):
        return self

    def encode(self, texts):
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True,
                                            show_progress_bar=False), dtype="float32")


def make_embedder():
    if config.EMBEDDINGS_BACKEND == "st":
        try:
            return STEmbedder(config.ST_MODEL)
        except Exception as e:
            log.warning("sentence-transformers unavailable (%s); using TF-IDF", e)
    return TfidfEmbedder()
