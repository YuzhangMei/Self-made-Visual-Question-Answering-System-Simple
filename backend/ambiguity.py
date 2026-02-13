import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

# 一些简单的“指代/含糊”关键词（可逐步扩展）
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

# 可选：如果问题里出现这些词，我们更倾向于认为用户在问“某个具体对象/位置”
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
    Example: "cup #2 (blue, right)"
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

    # 1) 指代词 / 含糊指代
    has_pronoun = _has_any_pattern(q, PRONOUN_PATTERNS)
    if has_pronoun:
        reasons.append("pronoun_reference")

    # 2) 多个同类对象（cup(2), bottle(3), ...）
    groups = _group_by_name(objects)
    multi_same_type: List[Tuple[str, int]] = []
    for name, objs in groups.items():
        if len(objs) >= 2:
            multi_same_type.append((name, len(objs)))

    for name, k in multi_same_type:
        reasons.append(f"multiple_objects_same_type: {name}({k})")

    # 3) 轻量判断“问题是否更像在指代某个具体对象”
    #    这是为了减少误报：比如问 "How many cups are there?" 就不该要求澄清哪个杯子
    asks_count = bool(re.search(r"\bhow many\b|\bnumber of\b|\bcount\b", q))
    asks_list_all = bool(re.search(r"\bwhat objects\b|\bwhat is in\b|\blist\b|\ball objects\b", q))
    has_referential_hint = _has_any_pattern(q, REFERENTIAL_HINTS)

    # 核心决策逻辑（保守、稳）
    # - 如果是计数问题或列举全体问题：通常不算“需要澄清的歧义”
    # - 否则：只要出现 pronoun 或者多同类对象，就算 ambiguous
    is_ambiguous = False
    if not asks_count and not asks_list_all:
        if has_pronoun or len(multi_same_type) > 0:
            is_ambiguous = True

    # 4) 生成澄清问题 + 候选项
    if is_ambiguous:
        # 优先：如果存在多同类对象，就对“最多的那一类”发问
        if len(multi_same_type) > 0:
            # pick the largest group
            target_name, _ = sorted(multi_same_type, key=lambda x: x[1], reverse=True)[0]
            target_objs = groups.get(target_name, [])
            options = [_summarize_obj(o, i + 1) for i, o in enumerate(target_objs)]
            clarifying_question = f"I see multiple {target_name}s. Which one do you mean?"
        else:
            # 只有 pronoun 但没有明显多同类对象
            # 给一个泛化澄清
            options = [_summarize_obj(o, i + 1) for i, o in enumerate(objects[:6])]
            clarifying_question = "Which object are you referring to?"

        # 如果问题本身有 referential hints（比如 left/right/next to），也保留 ambiguity 标记
        # 但不在 Phase 1 深挖解析（Phase 2/3 再做）
        if has_referential_hint:
            reasons.append("referential_hint_present")

    return {
        "is_ambiguous": is_ambiguous,
        "reasons": reasons,
        "clarifying_question": clarifying_question,
        "options": options,
    }
