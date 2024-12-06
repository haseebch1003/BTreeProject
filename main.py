import os
import struct

BLOCK_SIZE = 512
MAGIC_NUMBER = b"4337PRJ3"
MIN_DEGREE = 10
MAX_KEYS = 2 * MIN_DEGREE - 1
MAX_CHILDREN = 2 * MIN_DEGREE


class Node:
    def __init__(self, id, is_leaf=True):
        self.id = id
        self.parent_id = 0
        self.key_count = 0
        self.keys = [0] * MAX_KEYS
        self.values = [0] * MAX_KEYS
        self.children = [0] * MAX_CHILDREN
        self.is_leaf = is_leaf

    def serialize(self):
        data = (
            struct.pack(">Q", self.id)
            + struct.pack(">Q", self.parent_id)
            + struct.pack(">Q", self.key_count)
            + b"".join(struct.pack(">Q", key) for key in self.keys)
            + b"".join(struct.pack(">Q", value) for value in self.values)
            + b"".join(struct.pack(">Q", child) for child in self.children)
        )
        return data.ljust(BLOCK_SIZE, b'\x00')

    @classmethod
    def deserialize(cls, data):
        id = struct.unpack(">Q", data[0:8])[0]
        parent_id = struct.unpack(">Q", data[8:16])[0]
        key_count = struct.unpack(">Q", data[16:24])[0]
        keys = list(struct.unpack(">Q" * MAX_KEYS, data[24:24 + (8 * MAX_KEYS)]))
        values = list(struct.unpack(">Q" * MAX_KEYS, data[24 + (8 * MAX_KEYS):24 + (16 * MAX_KEYS)]))
        children = list(struct.unpack(">Q" * MAX_CHILDREN, data[24 + (16 * MAX_KEYS):24 + (16 * MAX_KEYS) + (8 * MAX_CHILDREN)]))
        node = cls(id, is_leaf=all(child == 0 for child in children))
        node.parent_id = parent_id
        node.key_count = key_count
        node.keys = keys
        node.values = values
        node.children = children
        return node


class Tree:
    def __init__(self, file):
        self.file = file
        self.root_id = 0
        self.next_id = 1

    def load_header(self):
        self.file.seek(0)
        header = self.file.read(BLOCK_SIZE)
        self.root_id = struct.unpack(">Q", header[8:16])[0]
        self.next_id = struct.unpack(">Q", header[16:24])[0]

    def update_header(self):
        self.file.seek(0)
        header = (
            MAGIC_NUMBER
            + struct.pack(">Q", self.root_id)
            + struct.pack(">Q", self.next_id)
        )
        self.file.write(header.ljust(BLOCK_SIZE, b'\x00'))

    def read_node(self, id):
        self.file.seek(id * BLOCK_SIZE)
        data = self.file.read(BLOCK_SIZE)
        return Node.deserialize(data)

    def write_node(self, node):
        self.file.seek(node.id * BLOCK_SIZE)
        self.file.write(node.serialize())

    def create_node(self, is_leaf=True):
        node = Node(self.next_id, is_leaf)
        self.next_id += 1
        self.write_node(node)
        return node

    def insert(self, key, value):
        if self.root_id == 0:
            root = self.create_node()
            root.keys[0] = key
            root.values[0] = value
            root.key_count = 1
            self.root_id = root.id
            self.update_header()
            self.write_node(root)
        else:
            root = self.read_node(self.root_id)
            if root.key_count == MAX_KEYS:
                new_root = self.create_node(is_leaf=False)
                new_root.children[0] = self.root_id
                self.split_child(new_root, 0, root)
                self.root_id = new_root.id
                self.update_header()
                self.insert_non_full(new_root, key, value)
            else:
                self.insert_non_full(root, key, value)

    def insert_non_full(self, node, key, value):
        i = node.key_count - 1
        if node.is_leaf:
            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.values[i + 1] = node.values[i]
                i -= 1
            node.keys[i + 1] = key
            node.values[i + 1] = value
            node.key_count += 1
            self.write_node(node)
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            child = self.read_node(node.children[i])
            if child.key_count == MAX_KEYS:
                self.split_child(node, i, child)
                if key > node.keys[i]:
                    i += 1
            self.insert_non_full(self.read_node(node.children[i]), key, value)

    def split_child(self, parent, index, child):
        new_child = self.create_node(is_leaf=child.is_leaf)
        new_child.key_count = MIN_DEGREE - 1
        for j in range(MIN_DEGREE - 1):
            new_child.keys[j] = child.keys[j + MIN_DEGREE]
            new_child.values[j] = child.values[j + MIN_DEGREE]
        if not child.is_leaf:
            for j in range(MIN_DEGREE):
                new_child.children[j] = child.children[j + MIN_DEGREE]
        child.key_count = MIN_DEGREE - 1
        for j in range(parent.key_count, index, -1):
            parent.children[j + 1] = parent.children[j]
        parent.children[index + 1] = new_child.id
        for j in range(parent.key_count - 1, index - 1, -1):
            parent.keys[j + 1] = parent.keys[j]
            parent.values[j + 1] = parent.values[j]
        parent.keys[index] = child.keys[MIN_DEGREE - 1]
        parent.values[index] = child.values[MIN_DEGREE - 1]
        parent.key_count += 1
        self.write_node(child)
        self.write_node(new_child)
        self.write_node(parent)

    def search(self, key, node=None):
        if node is None:
            node = self.read_node(self.root_id)
        i = 0
        while i < node.key_count and key > node.keys[i]:
            i += 1
        if i < node.key_count and key == node.keys[i]:
            return node.keys[i], node.values[i]
        if node.is_leaf:
            return None
        return self.search(key, self.read_node(node.children[i]))

    def print_tree(self, node=None, level=0):
        if node is None:
            node = self.read_node(self.root_id)
        print("  " * level + f"Node {node.id}: {node.keys[:node.key_count]}")
        if not node.is_leaf:
            for i in range(node.key_count + 1):
                self.print_tree(self.read_node(node.children[i]), level + 1)

    def extract(self, file_name):
        with open(file_name, "w") as f:
            self._extract_recursive(f, self.read_node(self.root_id))

    def _extract_recursive(self, f, node):
        for i in range(node.key_count):
            f.write(f"{node.keys[i]},{node.values[i]}\n")
        if not node.is_leaf:
            for i in range(node.key_count + 1):
                self._extract_recursive(f, self.read_node(node.children[i]))


def main():
    tree = None
    file = None

    while True:
        print("\nCommands: create, open, insert, search, load, print, extract, quit")
        command = input("Enter command: ").strip().lower()

        if command == "create":
            file_name = input("Enter file name: ").strip()
            if os.path.exists(file_name):
                overwrite = input(f"File {file_name} already exists. Overwrite? (yes/no): ").strip().lower()
                if overwrite != "yes":
                    print("Aborted.")
                    continue
            with open(file_name, "wb") as f:
                header = MAGIC_NUMBER + (0).to_bytes(8, "big") + (1).to_bytes(8, "big")
                f.write(header.ljust(BLOCK_SIZE, b'\x00'))
            print(f"File {file_name} created.")
            file = open(file_name, "r+b")
            tree = Tree(file)
            tree.load_header()

        elif command == "open":
            file_name = input("Enter file name: ").strip()
            if not os.path.exists(file_name):
                print(f"Error: File {file_name} does not exist.")
                continue
            with open(file_name, "rb") as f:
                header = f.read(BLOCK_SIZE)
                if header[:8] != MAGIC_NUMBER:
                    print(f"Error: File {file_name} is not a valid index file.")
                    continue
            file = open(file_name, "r+b")
            tree = Tree(file)
            tree.load_header()
            print(f"File {file_name} opened.")

        elif command == "insert":
            if not tree:
                print("Error: No index file is open.")
                continue
            try:
                key = int(input("Enter key: ").strip())
                value = int(input("Enter value: ").strip())
                tree.insert(key, value)
                print(f"Inserted key={key}, value={value}.")
            except ValueError:
                print("Error: Invalid input. Key and value must be integers.")

        elif command == "search":
            if not tree:
                print("Error: No index file is open.")
                continue
            try:
                key = int(input("Enter key: ").strip())
                result = tree.search(key)
                if result:
                    print(f"Found: key={result[0]}, value={result[1]}")
                else:
                    print(f"Key {key} not found.")
            except ValueError:
                print("Error: Invalid input. Key must be an integer.")

        elif command == "load":
            if not tree:
                print("Error: No index file is open.")
                continue
            file_name = input("Enter file name to load: ").strip()
            if not os.path.exists(file_name):
                print(f"Error: File {file_name} does not exist.")
                continue
            with open(file_name, "r") as f:
                for line in f:
                    try:
                        key, value = map(int, line.strip().split(","))
                        tree.insert(key, value)
                    except ValueError:
                        print(f"Error: Invalid line format '{line.strip()}'. Skipping.")
            print(f"Data loaded from {file_name}.")

        elif command == "print":
            if not tree:
                print("Error: No index file is open.")
                continue
            print("Printing B-Tree structure:")
            tree.print_tree()

        elif command == "extract":
            if not tree:
                print("Error: No index file is open.")
                continue
            file_name = input("Enter file name to extract to: ").strip()
            if os.path.exists(file_name):
                overwrite = input(f"File {file_name} already exists. Overwrite? (yes/no): ").strip().lower()
                if overwrite != "yes":
                    print("Aborted.")
                    continue
            tree.extract(file_name)
            print(f"Data extracted to {file_name}.")

        elif command == "quit":
            if file:
                file.close()
            print("Goodbye!")
            break

        else:
            print("Error: Unknown command.")


if __name__ == "__main__":
    main()
