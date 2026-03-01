import re

MARKER = '%'
MIN_LEN = 2


def extract_markers(text: str) -> list[str]:
    # Buggy starter: captures obvious matches but ignores edge rules.
    pattern = re.compile(rf"{re.escape(MARKER)}([A-Za-z0-9_]+)")
    return [match.group(1) for match in pattern.finditer(text)]
