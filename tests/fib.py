from __future__ import annotations
import heapq

def fib(n:int):
    my_fibs=[0,1]
    n=n-1
    if n==0:
        return 0
    elif n==1:
        return 1
    index = 1
    while index<n:
        next= my_fibs[index]+my_fibs[index-1]
        my_fibs.append(next)
        index=index+1
    return my_fibs[n]

def fib_map(n:int):
    fibs = {1:0, 2:1, 3:1, 4:2}
    if (n <= 4):
        return fibs.get(n)
    for i in range(5, n+1):
        val = fibs[i-1]+fibs[i-2]
        fibs[i] = val
    return fibs.get(n) 
        
print(f'fib_map n is {fib_map(7)}')


def fib_improved(n):
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a

def fib_improved_no_tuple(n) -> int:
    a = 0
    b = 1

    # can be _ or i.. If n was 5 the sequence for i 
    # would be 0 , 1, 2, 3, for range (n-1)
    for _ in range(n - 1):
        temp = a
        a = b
        b = temp + b
    return a

def is_palindrome(s: str) -> bool:
    left, right = 0, len(s) - 1
    while left < right:
        if s[left].lower() != s[right].lower():
            return False
        left += 1
        right -= 1
    return True
word = 'deed'
print(f"Is it a is_palindrome {word} : {is_palindrome(word)}")

def reverse_string(word: str) -> str:
    reversed = ''
    count = len(word) - 1
    while count >= 0:
        reversed += word[count]
        count -= 1
    return reversed

def rever_string_with_q(word: str) -> str:
    """Reverse a string using heapq with negative index priorities."""
    heap = []
    for i, char in enumerate(word):
        heapq.heappush(heap, (-i, char))

    reversed_chars = []
    while heap:
        _, char = heapq.heappop(heap)
        reversed_chars.append(char)

    return "".join(reversed_chars)

def reverse_string_with_stack(word: str) -> str:
    """Reverse a string using a LIFO stack."""
    stack = []
    for char in word:
        stack.append(char)

    reversed_chars = []
    while stack:
        reversed_chars.append(stack.pop())

    return "".join(reversed_chars)

word = 'bigturd'
print(f"reverse_string {word} : {reverse_string(word)}")
print(f"rever_string_with_q {word} : {rever_string_with_q(word)}")
print(f"reverse_string_with_stack {word} : {reverse_string_with_stack(word)}")

#0, 1 ,1 ,2 ,3 ,5
my_fib=fib(6)
print(f"The fib is : {my_fib}\n")
print(f"The improved fib is : {fib_improved(6)}\n")
print(f"The improved no tuple fib is : {fib_improved_no_tuple(6)}\n")


    
