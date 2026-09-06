import gaddag as gddg
from gaddag import GADDAG, GADDAGNode

def generate_moves(anchor_sq, current_gaddag_node, rack, board, cross_checks):
    current_sq = anchor_sq
    row, col = current_sq
    
    if not (0 <= row < len(board) and 0 <= col < len(board[0])):
        return
    
    # If the current square already has a tile on the board:
    if board[row][col] is not None:
        tile = board[row][col]
        # Follow the existing letter in the GADDAG without using rack tiles
        if tile in current_gaddag_node.children:
            next_sq = (row, col + 1)
            if col + 1 < len(board[row]):
                generate_moves(
                    next_sq,
                    current_gaddag_node.children[tile],
                    rack,  # Existing tile does not consume a tile from the rack
                    board,
                    cross_checks
                )
        return  # Stop here; do not place rack tiles on an occupied square
    
    # If the current square on the board is empty:
    if board[row][col] is None:
        valid_letters_for_square = cross_checks[(row, col)]
        
        # Try playing each unique tile currently in the AI's rack
        for tile in set(rack):
            
            # THE PRUNE: Does this tile create an invalid intersecting word?
            if tile not in valid_letters_for_square:
                continue # Skip this tile entirely, pruning the search tree
                
            # Does this tile exist in the current GADDAG node's children?
            if tile in current_gaddag_node.children:
                # Remove tile from rack
                new_rack = rack.copy()
                new_rack.remove(tile)
                
                # Recurse deeper into the GADDAG and onto the next board square
                next_sq = (row, col + 1)
                if col + 1 < len(board[row]):
                    generate_moves(
                        next_sq, 
                        current_gaddag_node.children[tile], 
                        new_rack, 
                        board, 
                        cross_checks
                    )

def get_vertical_word_part(board, row, col, direction="UP"):
    letters = []
    dir_upper = direction.upper() if isinstance(direction, str) else ""
    if dir_upper == "UP":
        r = row - 1
        while r >= 0 and board[r][col] is not None:
            letters.append(str(board[r][col]))
            r -= 1
        return "".join(reversed(letters))
    elif dir_upper == "DOWN":
        r = row + 1
        while r < len(board) and board[r][col] is not None:
            letters.append(str(board[r][col]))
            r += 1
        return "".join(letters)
    return ""

def calculate_cross_checks(board, dictionary):
    # Initialize all empty squares with the full alphabet
    cross_checks = {}
    full_alphabet = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    for row in range(15):
        for col in range(15):
            if board[row][col] is not None:
                continue # Skip occupied squares
                
            # Find contiguous letters above the empty square
            prefix = get_vertical_word_part(board, row, col, direction="UP")
            # Find contiguous letters below the empty square
            suffix = get_vertical_word_part(board, row, col, direction="DOWN")
            
            # If there are no tiles above or below, any letter is valid
            if not prefix and not suffix:
                cross_checks[(row, col)] = full_alphabet
                continue
                
            # Otherwise, test which letters form a valid word
            valid_letters = set()
            for letter in full_alphabet:
                test_word = prefix + letter + suffix
                if dictionary.is_valid_word(test_word):
                    valid_letters.add(letter)
                    
            cross_checks[(row, col)] = valid_letters
            
    return cross_checks