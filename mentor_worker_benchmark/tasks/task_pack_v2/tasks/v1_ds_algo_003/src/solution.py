def rank_products(records: list[tuple[str, int]], k: int) -> list[str]:
    if k <= 0:
        return []

    # Buggy starter: no aggregation and wrong ordering behavior.
    ordered = sorted(records, key=lambda item: (item[1], item[0]), reverse=True)
    return [name for name, _ in ordered[:k]]
