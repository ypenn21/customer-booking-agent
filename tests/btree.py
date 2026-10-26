from __future__ import annotations

_SENTINEL = object()

class BinaryTree:

    def __init__(self, value: int, left: BinaryTree | None = None, right: BinaryTree | None = None):
        self.left = left
        self.right = right
        self.value = value

    def add(self, node: BinaryTree):
        if node is None:
            return None

        if self.value > node.value:
            if self.left is None:
                self.left = node
            else:
                self.left.add(node)
        else:
            if self.right is None:
                self.right = node
            else:
                self.right.add(node)

    def traverse(self, node: BinaryTree | None | object = _SENTINEL) -> BinaryTree | None:
        if node is _SENTINEL:
            node = self
        if node is None:
            return None
        print(f"{node.value} " )
        left_last = self.traverse(node.left)
        right_last = self.traverse(node.right)

        return right_last or left_last or node

    # this is better without SENTINEL    
    def traverse(self) -> BinaryTree:
        if(self and self.value !=0):
            print(f"{self.value} ")
        if self.left:
            self.left.traverse()
        if self.right:
            self.right.traverse()


if __name__ == "__main__":
    root = BinaryTree(10)
    root.add(BinaryTree(5))
    root.add(BinaryTree(15))
    root.add(BinaryTree(20))
    root.add(BinaryTree(11))
    root.add(BinaryTree(7))

    last_node = root.traverse()
    print(f"Last node value: {last_node.value if last_node else None}")