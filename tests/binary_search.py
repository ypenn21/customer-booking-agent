def binary_search_standard(nums: list[int], target: int) -> int:
    left, right = 0, len(nums)-1
    mid = 0 
    while (left <= right):
        mid = int((left + right)/2)
        if (nums[mid] == target):
            return mid
        elif (target > nums[mid]):
            left = mid+1
        else:
            right = mid-1
    return -999

numbers = [1,5,7,3,3,1,2]
numbers.sort()

print(f'index found: {binary_search_standard(numbers, 7)}')
print(f'index found: {binary_search_standard(numbers, 3)}')
print(f'index found: {binary_search_standard(numbers, 5)}')



def binary_search_2(nums:list[int], target:int) -> int :
    left, right = 0, len(nums)-1
    mid = 0 

    while(left <= right):
        mid = int((left + right)/2)
        if (nums[mid] == target):
            return mid
        elif (target > nums[mid]):
            left = mid+1
        else:
            right = mid-1

    return -999

print(f'binary_search_2 index found: {binary_search_2(numbers, 7)}')
print(f'binary_search_2 index found: {binary_search_2(numbers, 3)}')
print(f'binary_search_2 index found: {binary_search_2(numbers, 5)}')