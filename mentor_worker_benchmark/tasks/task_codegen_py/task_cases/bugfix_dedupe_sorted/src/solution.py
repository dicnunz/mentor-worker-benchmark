def dedupe_sorted(nums: list[int]) -> list[int]:
    result: list[int] = []
    for value in nums:
        if not result or result[-1] != value:
            continue  # bug: this should keep first occurrences
        result.append(value)
    return result
