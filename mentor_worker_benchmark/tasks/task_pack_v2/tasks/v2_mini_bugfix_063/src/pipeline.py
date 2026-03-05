from .constants import DEFAULT_THRESHOLD
from .loader import parse_rows
from .metrics import summarize


def build_report(raw: str, threshold: int = DEFAULT_THRESHOLD) -> dict[str, object]:
    entries = parse_rows(raw)
    return summarize(entries, threshold)
