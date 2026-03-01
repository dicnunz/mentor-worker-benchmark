import math

import pytest

from src.solution import trimmed_mean


def _oracle(values: list[float], trim_ratio: float) -> float:
    if not 0 <= trim_ratio < 0.5:
        raise ValueError("trim_ratio must be in [0, 0.5)")

    filtered = [value for value in values if value == value]
    if not filtered:
        raise ValueError("no finite values")

    ordered = sorted(filtered)
    trim_count = int(len(ordered) * trim_ratio)
    kept = ordered[trim_count : len(ordered) - trim_count]
    if not kept:
        raise ValueError("all values were trimmed")
    return sum(kept) / len(kept)


def test_matches_oracle_for_mixed_values() -> None:
    values = [-1.78, 4.29, 16.09, 8.61, 11.61, -0.34, -3.67, -6.32, 99.5, nan]
    result = trimmed_mean(values, 0.1)
    assert result == pytest.approx(14.22111111111111, rel=1e-9, abs=1e-9)
    assert result == pytest.approx(_oracle(values, 0.1), rel=1e-9, abs=1e-9)


def test_invalid_trim_ratio_raises() -> None:
    with pytest.raises(ValueError):
        trimmed_mean([1.0, 2.0, 3.0], 0.5)


def test_all_nan_raises() -> None:
    with pytest.raises(ValueError):
        trimmed_mean([math.nan, math.nan], 0.1)
