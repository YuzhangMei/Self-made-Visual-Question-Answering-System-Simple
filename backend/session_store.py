import uuid
import time

# In-memory store (prototype). Production: Redis/DB.
SESSIONS = {}

DEFAULT_TTL_SECONDS = 15 * 60  # 15 minutes


def _now() -> float:
    return time.time()


def create_session(data: dict, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    session_id = str(uuid.uuid4())
    expires_at = _now() + ttl_seconds

    SESSIONS[session_id] = {
        "active": True,
        "created_at": _now(),
        "expires_at": expires_at,
        "history": [],     # list of {role, text}
        "focus_object": None,
        **data,
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    s = SESSIONS.get(session_id)
    if not s:
        return None
    # expire check
    if s.get("expires_at", 0) < _now():
        s["active"] = False
        return None
    if not s.get("active", False):
        return None
    return s


def end_session(session_id: str) -> bool:
    s = SESSIONS.get(session_id)
    if not s:
        return False
    s["active"] = False
    return True


def set_focus_object(session_id: str, obj: dict) -> bool:
    s = SESSIONS.get(session_id)
    if not s:
        return False
    s["focus_object"] = obj
    return True


def append_history(session_id: str, role: str, text: str) -> None:
    s = SESSIONS.get(session_id)
    if not s:
        return
    s.setdefault("history", []).append({"role": role, "text": text})
