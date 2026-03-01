def sum_positive(nums: list[int]) -> int:
    total = 0
    for value in nums:
        if value >= 0:
            total += value
        else:
            total += abs(value)  # bug: negatives should be ignored
    return total
