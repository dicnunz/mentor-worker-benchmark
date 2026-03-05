from .constants import DELIMITER


def parse_rows(raw: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(DELIMITER)]
        if len(parts) != 3:
            continue
        label, score_raw, bucket = parts
        try:
            score = int(score_raw)
        except ValueError:
            continue
        entries.append({"label": label.lower(), "score": score, "bucket": bucket.lower()})
    return entries
