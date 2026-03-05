DELIMITER = '|'


def parse_tasks(raw: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(DELIMITER)]
        if len(parts) != 4:
            continue
        name, owner, status, points_raw = parts
        try:
            points = int(points_raw)
        except ValueError:
            continue
        items.append(
            {
                "name": name.lower(),
                "owner": owner.lower(),
                "status": status.lower(),
                "points": points,
            }
        )
    return items
