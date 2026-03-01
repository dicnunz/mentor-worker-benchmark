from .aggregator import build_report
from .parser import parse_entries


def summarize(raw: str) -> dict[str, object]:
    entries = parse_entries(raw)
    return build_report(entries)
