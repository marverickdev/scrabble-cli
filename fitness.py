# A simplified static lookup table for tile leave values
LEAVE_VALUES = {
    '?': 14.0, 'S': 8.0, 'E': 2.5, 'A': 1.0, 'R': 1.5, 
    'T': 1.0, 'I': 0.5, 'D': 0.0, 'L': -0.5, 'N': -0.5, 
    'O': -1.0, 'C': -1.5, 'U': -2.0, 'M': -2.0, 'H': -2.5, 
    'P': -2.5, 'B': -3.0, 'Y': -3.0, 'G': -3.0, 'F': -4.0, 
    'W': -4.0, 'K': -4.5, 'V': -5.0, 'X': -6.0, 'J': -6.0, 
    'Z': -7.0, 'Q': -12.0
}

def evaluate_move(move, current_rack, board_state):
    # 1. Base Score (already calculated during generation)
    fitness = move.score 
    
    # 2. Determine the leave
    leave = list(current_rack)
    for tile in move.tiles_played:
        leave.remove(tile)
        
    # 3. Sum individual tile values
    leave_score = sum(LEAVE_VALUES[tile] for tile in leave)
    
    # 4. Apply Vowel/Consonant synergy penalty
    vowels = sum(1 for t in leave if t in "AEIOU")
    consonants = len(leave) - vowels
    
    if vowels > 4:
        leave_score -= (vowels - 4) * 3.0 # Heavy penalty for vowel flood
    elif consonants > 5:
        leave_score -= (consonants - 5) * 3.0 # Heavy penalty for consonant flood
        
    # Handle the Q/U dependency
    if 'Q' in leave and 'U' not in leave:
        leave_score -= 5.0 
        
    fitness += leave_score
    
    # 5. Apply Defensive Penalties (Pseudo-code)
    # if creates_easy_triple_word_access(move, board_state):
    #     fitness -= 15.0
        
    return fitness