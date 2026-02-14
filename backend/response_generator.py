from typing import List, Dict, Any
from collections import defaultdict


def _norm(s: str) -> str:
    return (s or "").strip()


def group_objects(objects: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group objects by name (type).
    """
    groups = defaultdict(list)
    for obj in objects:
        name = _norm(obj.get("name", "object")).lower()
        if not name:
            name = "object"
        groups[name].append(obj)
    return dict(groups)


def format_grouped_description(groups: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Human/screen-reader-friendly grouped description:
    - First provide totals
    - Then per-group details
    """
    # summary line
    summary_parts = []
    for name, objs in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        summary_parts.append(f"{len(objs)} {name}{'s' if len(objs) != 1 else ''}")
    summary_line = "I found " + ", ".join(summary_parts) + "."

    lines = [summary_line, ""]

    for name, objs in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        lines.append(f"{name.title()}s ({len(objs)}):")

        for obj in objs:
            obj_id = obj.get("id")
            count = obj.get("count", 1)
            color = obj.get("color")
            pos = obj.get("position")
            attrs = obj.get("attributes", [])

            detail_parts = []
            if obj_id is not None:
                detail_parts.append(f"Item {obj_id}")
            if count and int(count) != 1:
                detail_parts.append(f"count {count}")
            if color and str(color).lower() not in ["none", "null"]:
                detail_parts.append(str(color))
            if pos and str(pos).lower() != "unknown":
                detail_parts.append(f"at {pos}")
            if attrs and isinstance(attrs, list):
                # keep attributes short to be screen-reader friendly
                detail_parts.extend([str(a) for a in attrs[:3]])

            if detail_parts:
                lines.append("- " + ", ".join(detail_parts))
            else:
                lines.append("- (no additional details)")

        lines.append("")  # blank line between groups

    return "\n".join(lines).strip()


def generate_onepass_response(objects: List[Dict[str, Any]], ambiguity: Dict[str, Any] = None) -> str:
    """
    One-pass exhaustive response:
    - Explicitly acknowledge ambiguity if present
    - Provide grouped descriptions
    """
    if not objects:
        return "I do not see any salient objects in the image."

    groups = group_objects(objects)
    grouped_text = format_grouped_description(groups)

    prefix_lines = []
    if ambiguity and ambiguity.get("is_ambiguous"):
        reasons = ambiguity.get("reasons", [])
        # Acknowledge ambiguity in a user-friendly way
        prefix_lines.append("I notice the question may be ambiguous. Therefore, I will provide more information for you to disambiguite.")
        # If we have multi-object group info, mention it explicitly
        multi_groups = ambiguity.get("multi_object_groups", {})
        if multi_groups:
            # e.g., "multiple cups (2), multiple books (5)"
            parts = []
            for k, v in sorted(multi_groups.items(), key=lambda x: (-x[1], x[0])):
                parts.append(f"multiple {k}s ({v})")
            prefix_lines.append("Specifically, I see " + ", ".join(parts) + ".")
        #elif reasons:
        #    prefix_lines.append("Reason: " + ", ".join(reasons) + ".")
        prefix_lines.append("Here is a complete grouped description:")

    if prefix_lines:
        return "\n".join(prefix_lines) + "\n\n" + grouped_text

    return grouped_text


def generate_final_answer_grouped(
    question: str,
    selected_object: Dict[str, Any],
    all_objects: List[Dict[str, Any]],
    ambiguity: Dict[str, Any] = None
) -> str:
    """
    Final answer (after clarification or when not ambiguous):
    - Answer directly about the selected object
    - Still optionally provide grouped context (short)
    - Explicitly acknowledge ambiguity if it existed but has been resolved
    """
    if not selected_object:
        return "I could not determine the selected object."

    name = selected_object.get("name", "object")
    color = selected_object.get("color")
    pos = selected_object.get("position")
    obj_id = selected_object.get("id")

    parts = []
    if obj_id is not None:
        parts.append(f"{name} (item {obj_id})")
    else:
        parts.append(f"{name}")

    details = []
    if color and str(color).lower() not in ["none", "null"]:
        details.append(str(color))
    if pos and str(pos).lower() != "unknown":
        details.append(f"at {pos}")

    answer = f"You selected the {parts[0]}."
    if details:
        answer += " It is " + ", ".join(details) + "."

    # If ambiguity existed, say it was resolved
    if ambiguity and ambiguity.get("is_ambiguous"):
        answer = "Ambiguity resolved. " + answer

    # Add short grouped context (optional but nice)
    groups = group_objects(all_objects)
    summary = []
    for gname, objs in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        summary.append(f"{len(objs)} {gname}{'s' if len(objs) != 1 else ''}")
    answer += " Context: " + ", ".join(summary) + "."

    return answer
