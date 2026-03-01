import time

from src.solution import fibonacci


def test_fibonacci_values() -> None:
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(7) == 13


def test_negative_input_raises() -> None:
    try:
        fibonacci(-1)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for negative input")


def test_performance() -> None:
    start = time.perf_counter()
    value = fibonacci(35)
    duration = time.perf_counter() - start
    assert value == 9227465
    assert duration < 0.5
