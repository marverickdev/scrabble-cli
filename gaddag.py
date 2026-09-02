class GADDAGNode:
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
        # Iterate through every possible split point in the word
        for i in range(len(word)):
            # Reverse the prefix
            prefix = word[:i+1][::-1] 
            suffix = word[i+1:]
            
            current = self.root
            
            # 1. Insert the reversed prefix
            for char in prefix:
                if char not in current.children:
                    current.children[char] = GADDAGNode()
                current = current.children[char]
            
            # 2. Insert the pivot delimiter
            if self.delimiter not in current.children:
                current.children[self.delimiter] = GADDAGNode()
            current = current.children[self.delimiter]
            
            # 3. Insert the suffix
            for char in suffix:
                if char not in current.children:
                    current.children[char] = GADDAGNode()
                current = current.children[char]
            
            # Mark the final node as a valid word boundary
            current.is_word = True