from typing import List, Dict, Any

def generate_onepass_response(objects: List[Dict[str, Any]]) -> str:
    """
    Generate exhaustive structured description.
    Used for onepass mode.
    """
    if not objects:
        return "I do not see any objects in the image."

    lines = []
    lines.append(f"I see {len(objects)} objects in the image:")

    for obj in objects:
        name = obj.get("name", "object")
        color = obj.get("color", None)
        position = obj.get("position", None)
        count = obj.get("count", 1)

        description = f"- {count} {name}"
        details = []

        if color and str(color).lower() != "none":
            details.append(color)

        if position and str(position).lower() != "unknown":
            details.append(position)

        if details:
            description += f" ({', '.join(details)})"

        lines.append(description)

    return "\n".join(lines)


def generate_final_answer(question: str, objects: List[Dict[str, Any]]) -> str:
    """
    Simple answer generator for non-ambiguous case.
    For Phase 1 we keep it simple.
    """

    if not objects:
        return "I do not see any relevant objects."

    # Basic strategy: return first object summary
    obj = objects[0]
    name = obj.get("name", "object")
    color = obj.get("color", None)
    position = obj.get("position", None)

    answer = f"The object appears to be a {name}"

    details = []
    if color and str(color).lower() != "none":
        details.append(color)

    if position and str(position).lower() != "unknown":
        details.append(f"located on the {position}")

    if details:
        answer += " (" + ", ".join(details) + ")"

    return answer
