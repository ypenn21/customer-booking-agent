from __future__ import annotations

class LinkedList:

    def __init__(self, value: int, left: LinkedList | None = None , right : LinkedList | None = None):
        self.left = left
        self.right = right
        self.value = value
        self.end = right 

    def add(self, node: LinkedList):
        old_end_tmp = self.end
        self.end = node
        node.left = old_end_tmp 
        if old_end_tmp is not None:
            old_end_tmp.right = node
        else:
            # If there was no end node yet, node is the first right node
            node.left = self
            self.right = node

    def traverse(self, value: int):
        current = self
        while(current!=None):
            if current.value == value:
                break    
            current = current.right
        return current


root = LinkedList(0)
root.add(LinkedList(1))
root.add(LinkedList(2))
root.add(LinkedList(3))

found_node = root.traverse(3)
print(f"found: {found_node.value}")
print(f"found: {found_node.value} found left: {found_node.left.value}")

found_node = root.traverse(2)
print(f"found: {found_node.value} found left: {found_node.left.value} found right: {found_node.right.value}")