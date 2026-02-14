def detect_temporal_ambiguity(question: str, temporal_objects: list):
    """
    Detect ambiguity across time.
    """

    if not temporal_objects:
        return {
            "is_ambiguous": False
        }

    if len(temporal_objects) == 1:
        return {
            "is_ambiguous": False
        }

    # Ambiguous if multiple temporal objects exist
    options = []

    for obj in temporal_objects:
        first = obj["first_seen"]
        last = obj["last_seen"]

        if first == last:
            label = f"{obj['name']} at {first}"
        else:
            label = f"{obj['name']} ({first}–{last})"

        options.append(label)

    clarify_question = (
        "I see multiple objects across time. "
        "Which one are you referring to?"
    )

    return {
        "is_ambiguous": True,
        "clarifying_question": clarify_question,
        "options": options,
    }
