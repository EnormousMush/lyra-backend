"""
sessions.py — In-memory session store for uploaded songs.

A "session" holds the extracted features for one uploaded song plus the
chat history about it. Single-process / single-session-scope: no
persistence, no cross-process sharing. Lost on server restart.
"""

import uuid
from typing import Any


_sessions: dict[str, dict[str, Any]] = {}


def create_session(features: dict, metadata: dict | None = None) -> str:
    """Register a new session. Returns the session id."""
    sid = uuid.uuid4().hex[:12]
    _sessions[sid] = {
        "features": features,
        "metadata": metadata or {},
        "history": [],  # list[{"role": "user"|"assistant", "content": str}]
    }
    return sid


def get_session(sid: str) -> dict | None:
    return _sessions.get(sid)


def append_message(sid: str, role: str, content: str) -> None:
    s = _sessions.get(sid)
    if s is not None:
        s["history"].append({"role": role, "content": content})


def delete_session(sid: str) -> None:
    _sessions.pop(sid, None)
