def rank_products(records: list[tuple[str, int]], k: int) -> list[str]:
    if k <= 0:
        return []

    scores: dict[str, int] = {}
    for name, delta in records:
        scores[name] = scores.get(name, 0) + delta

    ordered = sorted(
        [(name, score) for name, score in scores.items() if score > 0],
        key=lambda item: (-item[1], item[0]),
    )
    # Bug: off-by-one slice.
    return [name for name, _ in ordered[: k + 1]]
