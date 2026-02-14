from collections import defaultdict


def aggregate_temporal_objects(frame_results):
    """
    frame_results:
        [
          (timestamp, objects),
          (timestamp, objects),
        ]
    """

    object_map = defaultdict(lambda: {
        "name": None,
        "first_seen": None,
        "last_seen": None,
        "count": 0
    })

    for timestamp, objects in frame_results:
        for obj in objects:
            key = obj["name"]  # prototype: group by name only

            if object_map[key]["name"] is None:
                object_map[key]["name"] = key
                object_map[key]["first_seen"] = timestamp

            object_map[key]["last_seen"] = timestamp
            object_map[key]["count"] += 1

    return list(object_map.values())
