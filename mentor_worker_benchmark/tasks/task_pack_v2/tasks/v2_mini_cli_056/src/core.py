def evaluate(values: list[int], *, mode: str, bias: int) -> int:
    if not values:
        raise ValueError("values cannot be empty")
    if mode == "sum":
        return sum(values) + bias
    if mode == "max":
        return max(values) + bias
    # Buggy: missing median support.
    raise ValueError(f"unsupported mode: {mode}")
