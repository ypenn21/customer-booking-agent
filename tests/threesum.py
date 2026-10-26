def three_sum(nums: list[int]) -> list[list[int]]:
    """Find all unique triplets that sum to zero using three loops. O(n³) time."""
    nums.sort()
    n = len(nums)
    result = set()

    for i in range(n):
        # if i > 0 and nums[i] == nums[i - 1]:
        #     continue
        for j in range(i + 1, n):
            # if j > i + 1 and nums[j] == nums[j - 1]:
            #     continue
            for k in range(j + 1, n):
                # if k > j + 1 and nums[k] == nums[k - 1]:
                #     continue
                if nums[i] + nums[j] + nums[k] == 0:
                    result.add((nums[i], nums[j], nums[k]))

    return result #   If want to return a list of lists return [list(t) for t in result]  # 3. Convert 

input = [3, -1, -2, 4, 5, 6, -5, -6, -11, -2,-1,3]

print(three_sum(input))