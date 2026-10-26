def longest_substring_k_distinct(s: str, k: int) -> int:
    """Longest substring with at most k distinct characters. O(n) time."""
    from collections import defaultdict

    char_count = defaultdict(int)
    left = 0
    max_length = 0

    for right in range(len(s)):
        char_count[s[right]] += 1

        # Shrink window while we have more than k distinct chars
        while len(char_count) > k:
            char_count[s[left]] -= 1
            if char_count[s[left]] == 0:
                del char_count[s[left]]
            left += 1

        max_length = max(max_length, right - left + 1)

    return max_length

count = longest_substring_k_distinct("abaccc", 2)
print(count)
count = longest_substring_k_distinct("abacccr", 3)
print(count)