def summarize(entries: list[dict[str, object]], threshold: int) -> dict[str, object]:
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    total = sum(int(item["score"]) for item in entries)
    # Buggy: threshold comparison should be strict '>'.
    above_threshold = sum(1 for item in entries if int(item["score"]) >= threshold)
    # Buggy: chooses last label, not highest-scoring label.
    top_label = str(entries[-1]["label"]) if entries else None
    return {
        "total": total,
        "count": len(entries),
        "above_threshold": above_threshold,
        "top_label": top_label,
    }
