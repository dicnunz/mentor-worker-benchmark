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
    values = [14.94, -5.93, 4.87, 13.85, -1.8, 1.63, 16.98, 12.19, 87.0, nan]
    result = trimmed_mean(values, 0.25)
    assert result == pytest.approx(9.495999999999999, rel=1e-9, abs=1e-9)
    assert result == pytest.approx(_oracle(values, 0.25), rel=1e-9, abs=1e-9)


def test_invalid_trim_ratio_raises() -> None:
    with pytest.raises(ValueError):
        trimmed_mean([1.0, 2.0, 3.0], 0.5)


def test_all_nan_raises() -> None:
    with pytest.raises(ValueError):
        trimmed_mean([math.nan, math.nan], 0.1)

def test_single_value_no_trim() -> None:
    assert trimmed_mean([5.0], 0.0) == pytest.approx(5.0)

def test_negative_trim_ratio_raises() -> None:
    with pytest.raises(ValueError):
        trimmed_mean([1.0, 2.0, 3.0], -0.1)
