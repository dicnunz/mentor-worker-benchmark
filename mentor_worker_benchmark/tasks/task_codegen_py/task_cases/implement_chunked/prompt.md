# Task: Implement `chunked`

Implement `chunked(items: list[int], size: int) -> list[list[int]]` in `src/solution.py`.

Rules:
- Split `items` into consecutive chunks of length `size`.
- Final chunk may be shorter.
- Raise `ValueError` if `size <= 0`.
