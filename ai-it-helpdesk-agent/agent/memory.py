"""
memory.py
---------
Per-session memory for the agent: conversation history plus lightweight
issue-tracking state (how many times the user has reported the same
problem is unresolved, which is used to trigger escalation).

Memory is persisted to a small JSON file per session under data/sessions/
so a conversation can resume across separate runs of the app/CLI.
"""

import json
import os
from datetime import datetime, timezone

_SESSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "sessions",
)

MAX_HISTORY_FOR_CONTEXT = 8  # how many recent turns to feed back to the agent


class ConversationMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        os.makedirs(_SESSIONS_DIR, exist_ok=True)
        self._path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
        self._state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "session_id": self.session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "unresolved_streak": 0,
            "last_category": None,
        }

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def add_message(self, role: str, content: str, meta: dict = None):
        self._state["messages"].append(
            {
                "role": role,
                "content": content,
                "meta": meta or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save()

    def recent_history(self, n: int = MAX_HISTORY_FOR_CONTEXT) -> list:
        return self._state["messages"][-n:]

    def set_last_category(self, category: str):
        self._state["last_category"] = category
        self._save()

    def get_last_category(self):
        return self._state.get("last_category")

    def mark_unresolved(self):
        self._state["unresolved_streak"] = self._state.get("unresolved_streak", 0) + 1
        self._save()
        return self._state["unresolved_streak"]

    def reset_unresolved(self):
        self._state["unresolved_streak"] = 0
        self._save()

    def get_unresolved_streak(self) -> int:
        return self._state.get("unresolved_streak", 0)

    def to_dict(self) -> dict:
        return self._state
