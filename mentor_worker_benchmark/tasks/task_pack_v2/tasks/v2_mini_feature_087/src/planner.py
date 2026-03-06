def build_plan(
    items: list[dict[str, object]],
    *,
    min_points: int,
    include_deferred: bool = False,
) -> list[dict[str, object]]:
    filtered = []
    for item in items:
        points = int(item["points"])
        status = str(item["status"])
        if points < min_points:
            continue
        # Buggy: this still excludes deferred items even when include_deferred=True.
        if status == "deferred":
            continue
        filtered.append(item)
    return sorted(filtered, key=lambda item: (-int(item["points"]), str(item["name"])))
