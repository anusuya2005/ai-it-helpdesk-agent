"""
knowledge_base.py
------------------
Loads the IT issue knowledge base (data/knowledge_base.json) used as the
retrieval corpus for the RAG component of the agent.
"""

import json
import os

_KB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "knowledge_base.json",
)


def load_knowledge_base(path: str = _KB_PATH) -> list:
    """Load and return the knowledge base as a list of dicts.

    Each entry has: id, category, title, keywords, solution (list of steps).
    """
    with open(path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    return kb


def build_document_text(entry: dict) -> str:
    """Flatten a KB entry into a single searchable text blob."""
    parts = [
        entry.get("title", ""),
        entry.get("category", ""),
        " ".join(entry.get("keywords", [])),
        " ".join(entry.get("solution", [])),
    ]
    return " ".join(parts)


def list_categories(kb: list) -> list:
    """Return the sorted unique list of categories present in the KB."""
    return sorted({entry["category"] for entry in kb})
