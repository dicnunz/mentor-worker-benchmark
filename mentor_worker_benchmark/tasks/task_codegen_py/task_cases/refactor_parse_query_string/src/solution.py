def parse_query_string(query: str) -> dict[str, object]:
    result: dict[str, object] = {}
    if not query:
        return result

    for part in query.split("&"):
        if not part:
            continue
        key, value = part.split("=", 1)
        result[key] = value

    return result
