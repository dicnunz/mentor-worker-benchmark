def build_report(entries: list[tuple[str, int]]) -> dict[str, object]:
    total = 0
    keys: list[str] = []
    values: list[int] = []
    for key, value in entries:
        total += value
        keys.append(key)
        values.append(value)

    return {
        "total": total,
        "unique_keys": len(set(keys)),
        "top_key": keys[-1] if keys else None,
        "top_value": values[-1] if values else None,
    }
