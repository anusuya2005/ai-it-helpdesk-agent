"""
rag.py
------
A dependency-free Retrieval-Augmented Generation (RAG) component.

Implements TF-IDF vectorization and cosine similarity from scratch using
only the Python standard library, so the retriever runs anywhere without
needing scikit-learn, numpy, or a vector database. This keeps the project
easy to clone, install, and grade.

For larger real-world knowledge bases, swap this module for a proper
vector store (FAISS, Chroma, pgvector) without changing the Agent's API.
"""

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "at", "for", "with", "and", "or", "but", "not",
    "my", "your", "it", "its", "this", "that", "i", "me", "we", "you",
    "do", "does", "did", "can", "cannot", "cant", "wont", "will", "have",
    "has", "had", "so", "up", "down", "out", "as", "if", "than",
}


def tokenize(text: str) -> list:
    """Lowercase, strip punctuation, and remove common stopwords.

    Hyphens between letters are collapsed first (e.g. "Wi-Fi" -> "wifi",
    "e-mail" -> "email") so common compound IT terms match as one token.
    """
    text = re.sub(r"(?<=[a-zA-Z])-(?=[a-zA-Z])", "", text.lower())
    tokens = _TOKEN_RE.findall(text)
    return [t for t in tokens if t not in _STOPWORDS]


class TfidfRetriever:
    """A minimal TF-IDF retriever over a fixed corpus of documents."""

    def __init__(self, documents: list, doc_ids: list = None):
        """
        documents: list[str] -- raw text for each document
        doc_ids:   list[Any] -- optional parallel list of identifiers
        """
        self.documents = documents
        self.doc_ids = doc_ids if doc_ids is not None else list(range(len(documents)))
        self._tokenized = [tokenize(doc) for doc in documents]
        self._doc_freq = self._compute_doc_freq(self._tokenized)
        self._n_docs = len(documents)
        self._doc_vectors = [
            self._tfidf_vector(tokens) for tokens in self._tokenized
        ]

    @staticmethod
    def _compute_doc_freq(tokenized_docs: list) -> Counter:
        df = Counter()
        for tokens in tokenized_docs:
            for term in set(tokens):
                df[term] += 1
        return df

    def _idf(self, term: str) -> float:
        # Smoothed IDF to avoid division by zero / negative values
        df = self._doc_freq.get(term, 0)
        return math.log((1 + self._n_docs) / (1 + df)) + 1.0

    def _tfidf_vector(self, tokens: list) -> dict:
        if not tokens:
            return {}
        term_counts = Counter(tokens)
        max_count = max(term_counts.values())
        vector = {}
        for term, count in term_counts.items():
            tf = 0.5 + 0.5 * (count / max_count)  # augmented term frequency
            vector[term] = tf * self._idf(term)
        return vector

    @staticmethod
    def _cosine_similarity(vec_a: dict, vec_b: dict) -> float:
        if not vec_a or not vec_b:
            return 0.0
        # iterate over the smaller vector for speed
        if len(vec_a) > len(vec_b):
            vec_a, vec_b = vec_b, vec_a
        dot = sum(weight * vec_b.get(term, 0.0) for term, weight in vec_a.items())
        norm_a = math.sqrt(sum(w * w for w in vec_a.values()))
        norm_b = math.sqrt(sum(w * w for w in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def query(self, text: str, top_k: int = 3) -> list:
        """Return top_k (doc_id, score, document_text) tuples, best first."""
        query_tokens = tokenize(text)
        query_vector = self._tfidf_vector(query_tokens)
        scored = [
            (self.doc_ids[i], self._cosine_similarity(query_vector, self._doc_vectors[i]), self.documents[i])
            for i in range(self._n_docs)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
