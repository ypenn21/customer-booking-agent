from __future__ import annotations
from typing import Any


class Node:
    """Doubly Linked List node for storing key-value pairs."""

    def __init__(self, key: Any = 0, value: Any = 0):
        self.key: Any = key
        self.value: Any = value
        self.prev: Node | None = None
        self.next: Node | None = None


class LRUCache:
    """
    Least Recently Used (LRU) Cache implementation using a Hash Map and a Doubly Linked List.
    Provides O(1) time complexity for both get and put operations.
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than 0")

        self.capacity: int = capacity
        self.cache: dict[Any, Node] = {}

        # Dummy head and tail nodes to avoid edge cases with empty list boundary operations
        self.head: Node = Node()
        self.tail: Node = Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _add_node(self, node: Node) -> None:
        """Always add the new node right after dummy head (Most Recently Used)."""
        node.prev = self.head
        node.next = self.head.next

        if self.head.next:
            self.head.next.prev = node
        self.head.next = node

    def _remove_node(self, node: Node) -> None:
        """Remove an existing node from the doubly linked list."""
        prev_node = node.prev
        next_node = node.next

        if prev_node:
            prev_node.next = next_node
        if next_node:
            next_node.prev = prev_node

    def _move_to_head(self, node: Node) -> None:
        """Move an accessed or updated node to the head (mark as MRU)."""
        self._remove_node(node)
        self._add_node(node)

    def _pop_tail(self) -> Node | None:
        """Pop the current least recently used (LRU) node before dummy tail."""
        res = self.tail.prev
        if res and res is not self.head:
            self._remove_node(res)
            return res
        return None

    def get(self, key: Any) -> Any:
        """
        Get the value of the key if the key exists in the cache, otherwise return -1.
        Moves the accessed node to the MRU position.
        """
        if key not in self.cache:
            return -1

        node = self.cache[key]
        self._move_to_head(node)
        return node.value

    def put(self, key: Any, value: Any) -> None:
        """
        Update the value of the key if the key exists, or insert key-value pair if not.
        Evicts the least recently used item if cache capacity is exceeded.
        """
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            if len(self.cache) >= self.capacity:
                lru_node = self._pop_tail()
                if lru_node:
                    del self.cache[lru_node.key]

            new_node = Node(key, value)
            self.cache[key] = new_node
            self._add_node(new_node)


if __name__ == "__main__":
    cache = LRUCache(2)

    cache.put(1, 1)
    cache.put(2, 2)
    print("get(1):", cache.get(1))  # returns 1

    cache.put(3, 3)                # evicts key 2
    print("get(2):", cache.get(2))  # returns -1 (not found)

    cache.put(4, 4)                # evicts key 1
    print("get(1):", cache.get(1))  # returns -1 (not found)
    print("get(3):", cache.get(3))  # returns 3
    print("get(4):", cache.get(4))  # returns 4
