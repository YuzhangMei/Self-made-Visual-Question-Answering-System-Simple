import re
from collections import defaultdict
from difflib import SequenceMatcher


def normalize_name(name: str) -> str:
    name = name.lower()

    # remove descriptive phrases
    name = re.sub(r"with .*", "", name)

    # take last word
    words = name.split()
    if not words:
        return name

    base = words[-1]

    # remove plural
    if base.endswith("s"):
        base = base[:-1]

    return base.strip()


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def aggregate_temporal_objects(frame_results):

    object_map = {}

    for timestamp, objects in frame_results:
        for obj in objects:
            key = normalize_name(obj["name"])
            # try to merge with existing similar key
            matched_key = None
            for existing_key in object_map.keys():
                if similar(existing_key, key) > 0.75:
                    matched_key = existing_key
                    break

            if matched_key:
                key = matched_key

            IGNORE = {"scene", "room", "furniture"}
            if key in IGNORE:
                continue
            if key not in object_map:
                object_map[key] = {
                    "name": key,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                }
            else:
                object_map[key]["last_seen"] = timestamp

    return list(object_map.values())

