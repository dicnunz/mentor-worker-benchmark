SEPARATOR = '|'


def parse_entries(raw: str, separator: str = SEPARATOR) -> list[tuple[str, int]]:
    entries: list[tuple[str, int]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        key, value = line.split(separator)
        entries.append((key.strip(), int(value)))
    return entries
