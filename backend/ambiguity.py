import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

# Simple pronouns (to be extended)
PRONOUN_PATTERNS = [
    r"\bit\b",
    r"\bthis\b",
    r"\bthat\b",
    r"\bthese\b",
    r"\bthose\b",
    r"\bthing\b",
    r"\bone\b",
    r"\bhere\b",
    r"\bthere\b",
    r"\bthe one\b",
    r"\bthat one\b",
]

# If the words below exist in the question, we tend to believe that
# the user is asking for a specific object.
REFERENTIAL_HINTS = [
    r"\bwhich\b",
    r"\bwhere\b",
    r"\bwhat\b",
    r"\bwhose\b",
    r"\bon the left\b",
    r"\bon the right\b",
    r"\bnext to\b",
    r"\bnear\b",
    r"\bclosest\b",
    r"\bfarthest\b",
]

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _has_any_pattern(text: str, patterns: List[str]) -> bool:
    t = _norm(text)
    for p in patterns:
        if re.search(p, t):
            return True
    return False

def _summarize_obj(obj: Dict[str, Any], idx_fallback: int) -> str:
    """
    Produce a short human-readable label for clarifying options.
    """
    obj_id = obj.get("id", idx_fallback)
    name = obj.get("name", "object")
    color = obj.get("color", None)
    pos = obj.get("position", None)

    parts = [f"{name} #{obj_id}"]
    meta = []
    if color and str(color).lower() != "none":
        meta.append(str(color))
    if pos and str(pos).lower() != "unknown":
        meta.append(str(pos))
    if meta:
        parts.append(f"({', '.join(meta)})")
    return " ".join(parts)

def _group_by_name(objects: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    groups = defaultdict(list)
    for obj in objects:
        name = _norm(obj.get("name", "object"))
        if not name:
            name = "object"
        groups[name].append(obj)
    return dict(groups)

def detect_ambiguity(question: str, objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Rule-based ambiguity detector.

    Returns:
    {
      "is_ambiguous": bool,
      "reasons": [str],
      "clarifying_question": str or None,
      "options": [str]  # human-readable options for the user
    }
    """
    q = _norm(question)
    reasons: List[str] = []
    options: List[str] = []
    clarifying_question = None

    # Pronouns
    has_pronoun = _has_any_pattern(q, PRONOUN_PATTERNS)
    if has_pronoun:
        reasons.append("pronoun_reference")

    # Multiple objects within the same class
    groups = _group_by_name(objects)
    multi_same_type: List[Tuple[str, int]] = []
    for name, objs in groups.items():
        if len(objs) >= 2:
            multi_same_type.append((name, len(objs)))

    for name, k in multi_same_type:
        reasons.append(f"multiple_objects_same_type: {name}({k})")

    multi_object_groups = {name: k for name, k in multi_same_type}

    # Make judgment on whether the question is referring to a specific object
    # To reduce mistakes in reply
    asks_count = bool(re.search(r"\bhow many\b|\bnumber of\b|\bcount\b", q))
    asks_list_all = bool(re.search(r"\bwhat objects\b|\bwhat is in\b|\blist\b|\ball objects\b", q))
    has_referential_hint = _has_any_pattern(q, REFERENTIAL_HINTS)

    is_ambiguous = False
    if not asks_count and not asks_list_all:
        if has_pronoun or len(multi_same_type) > 0:
            is_ambiguous = True

    # Generate candidate questions
    if is_ambiguous:
        # If multiple groups exist, pick the largest one
        if len(multi_same_type) > 0:
            target_name, _ = sorted(multi_same_type, key=lambda x: x[1], reverse=True)[0]
            target_objs = groups.get(target_name, [])
            options = [_summarize_obj(o, i + 1) for i, o in enumerate(target_objs)]
            clarifying_question = f"I see multiple {target_name}s. Which one do you mean?"
        else:
            # Only pronouns without a multi-object class
            # -> Return a generalized clarifying question
            options = [_summarize_obj(o, i + 1) for i, o in enumerate(objects[:6])]
            clarifying_question = "Which object are you referring to?"

        # Preserve ambiguity even if the question already contains referential hints
        # But not explore in the first round (in the following rounds instead)
        if has_referential_hint:
            reasons.append("referential_hint_present")

    return {
        "is_ambiguous": is_ambiguous,
        "reasons": reasons,
        "clarifying_question": clarifying_question,
        "options": options,
        "multi_object_groups": multi_object_groups,
    }
