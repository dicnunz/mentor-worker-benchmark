def trimmed_mean(values: list[float], trim_ratio: float) -> float:
    if not values:
        raise ValueError("values must not be empty")

    # Buggy starter: no NaN handling, no trimming, no ratio validation.
    return sum(values) / len(values)
