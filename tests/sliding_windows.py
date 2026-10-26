# =============================================================================
# SECTION 3: SLIDING WINDOW PATTERN
# =============================================================================
# Use when: Contiguous subarrays/substrings, max/min in window, fixed or variable size

def max_sum_subarray_fixed(arr: list[int], k: int) -> int:
    """Maximum sum of any subarray of size k. O(n) time."""
    if len(arr) < k:
        return 0

    window_sum = sum(arr[:k])
    max_sum = window_sum

    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]  # Slide: add new, remove old
        max_sum = max(max_sum, window_sum)

    return max_sum