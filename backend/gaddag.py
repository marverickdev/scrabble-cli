class GADDAGNode:
    __slots__ = ('children', 'is_word')

    def __init__(self):
        # Maps a character (e.g., 'A') to the next GADDAGNode
        self.children = {}
        # True if a path ending here forms a valid word
        self.is_word = False


class GADDAG:
    def __init__(self):
        self.root = GADDAGNode()
        self.delimiter = '>'

    def add_word(self, word):
        L = len(word)
        delim = self.delimiter

        # Iterate through every possible split point in the word
        for i in range(L):
            current = self.root

            # 1. Insert the reversed prefix word[:i+1][::-1]
            for j in range(i, -1, -1):
                c = word[j]
                node = current.children.get(c)
                if node is None:
                    node = GADDAGNode()
                    current.children[c] = node
                current = node

            # 2. Insert the pivot delimiter
            node = current.children.get(delim)
            if node is None:
                node = GADDAGNode()
                current.children[delim] = node
            current = node

            # 3. Insert the suffix word[i+1:]
            for j in range(i + 1, L):
                c = word[j]
                node = current.children.get(c)
                if node is None:
                    node = GADDAGNode()
                    current.children[c] = node
                current = node

            # Mark the final node as a valid word boundary
            current.is_word = True

    def is_valid_word(self, word):
        if not word:
            return False
        current = self.root
        path = word[0] + self.delimiter + word[1:]
        for char in path:
            if char not in current.children:
                return False
            current = current.children[char]
        return current.is_word