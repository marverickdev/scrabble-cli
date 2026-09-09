import random
import time

# ---------------------------------------------------------
# CONSTANTS & MASKS
# ---------------------------------------------------------

# 26 bits set to 1 (0b11111111111111111111111111) -> 0x3FFFFFF
# Represents a square where ANY letter A-Z is valid.
ALL_LETTERS_ALLOWED = 0x3FFFFFF


# ---------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------

class Move:
    """
    A lightweight container for a generated move.
    Uses __slots__ to prevent Python from allocating a memory-heavy __dict__ 
    for every single move object generated.
    """
    __slots__ = ['score', 'heuristic_fitness', 'tiles_played']
    
    def __init__(self, score, heuristic_fitness, tiles_played):
        self.score = score
        self.heuristic_fitness = heuristic_fitness
        self.tiles_played = tiles_played


class SimState:
    """
    1D Padded Array Board Representation.
    Scrabble is 15x15. We pad it to 16x16 (256 length) to allow fast bitwise
    coordinate math and eliminate out-of-bounds checks during traversal.
    """
    __slots__ = ['board', 'cross_checks']
    
    def __init__(self):
        # bytearray of size 256. 
        # 0 = empty space
        # 255 = out of bounds (the padding)
        # 65-90 = ASCII values for placed letters A-Z
        self.board = bytearray(256)
        
        # 1D array of 32-bit integers representing allowed letters (bitmasks)
        self.cross_checks = [ALL_LETTERS_ALLOWED] * 256
        
        # Initialize the 16th column and 16th row as Out of Bounds (255)
        for i in range(256):
            row = i >> 4  # Fast bitwise integer division by 16
            col = i & 15  # Fast bitwise modulo 16
            
            if row == 15 or col == 15:
                self.board[i] = 255
                self.cross_checks[i] = 0 # No letters allowed out of bounds
                
    def fast_clone(self):
        """
        Bypasses standard deepcopy for maximum performance during simulations.
        Allocates memory as a direct block copy.
        """
        clone = SimState.__new__(SimState)
        clone.board = self.board[:]                   # Fast memory block slice
        clone.cross_checks = self.cross_checks.copy() # Shallow primitive list copy
        return clone

    def apply_move(self, move):
        """
        Applies a Move object to this specific board state.
        (Placeholder for your actual tile-placement logic)
        """
        # Example pseudo-logic:
        # for square_index, letter in move.tiles_played:
        #     self.board[square_index] = ord(letter)
        pass


# ---------------------------------------------------------
# SIMULATION LOGIC
# ---------------------------------------------------------

def get_unseen_tiles(total_tile_distribution, current_board, ai_rack):
    """
    Calculates the pool of tiles remaining in the bag and the opponent's rack.
    """
    unseen = total_tile_distribution.copy()
    
    # Remove all tiles currently visible on the board
    for char_code in current_board.board:
        if 65 <= char_code <= 90: # If it's A-Z
            letter = chr(char_code)
            if letter in unseen:
                unseen.remove(letter)
                
    # Remove the AI's known rack tiles
    for tile in ai_rack:
        if tile in unseen:
            unseen.remove(tile)
            
    return unseen


def generate_moves_mock(state, rack):
    """
    Placeholder for your GADDAG move generator.
    In production, this takes the board state and the rack, and returns valid moves.
    """
    return [
        Move(
            score=random.randint(10, 40), 
            heuristic_fitness=random.randint(10, 40), 
            tiles_played=[]
        )
    ]


def get_best_move_monte_carlo(candidate_moves, initial_state, ai_rack, total_tile_distribution, iterations=500):
    """
    The main Monte Carlo simulation loop.
    """
    best_move = None
    max_expected_value = -float('inf')
    
    # 1. Determine what tiles are left in the wild
    unseen_tiles = get_unseen_tiles(total_tile_distribution, initial_state, ai_rack)
    
    # 2. Pre-filter: Only simulate the top 15 moves to save computation time
    top_candidates = sorted(
        candidate_moves, 
        key=lambda m: m.heuristic_fitness, 
        reverse=True
    )[:15]

    for ai_move in top_candidates:
        total_differential = 0
        
        # 3. Clone the state once per AI candidate move
        simulated_state = initial_state.fast_clone()
        simulated_state.apply_move(ai_move)
        
        # 4. Run the simulations
        for _ in range(iterations):
            
            # Deal 7 random tiles to the phantom opponent
            random.shuffle(unseen_tiles)
            phantom_rack = unseen_tiles[:7]
            
            # Generate the phantom human's legal responses
            phantom_responses = generate_moves_mock(simulated_state, phantom_rack)
            
            if not phantom_responses:
                # If human has no valid moves, AI keeps its full points
                total_differential += ai_move.score
                continue
                
            # Assume the human plays their best heuristic move
            best_phantom_response = max(phantom_responses, key=lambda m: m.heuristic_fitness)
            
            # Calculate Delta (AI points minus Human points)
            differential = ai_move.score - best_phantom_response.score
            total_differential += differential
            
        # 5. Average the differential across all iterations
        expected_value = total_differential / iterations
        
        # 6. Update the best move if this EV is higher
        if expected_value > max_expected_value:
            max_expected_value = expected_value
            best_move = ai_move
            
    return best_move, max_expected_value


# ---------------------------------------------------------
# EXECUTION & TESTING
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Initializing fast board state...")
    state = SimState()
    
    # Standard NASPA 100-tile distribution
    standard_distribution = (
        ['?']*2 + ['E']*12 + ['A']*9 + ['I']*9 + ['O']*8 + ['N']*6 + ['R']*6 + 
        ['T']*6 + ['L']*4 + ['S']*4 + ['U']*4 + ['D']*4 + ['G']*3 + ['B']*2 + 
        ['C']*2 + ['M']*2 + ['P']*2 + ['F']*2 + ['H']*2 + ['V']*2 + ['W']*2 + 
        ['Y']*2 + ['K']*1 + ['J']*1 + ['X']*1 + ['Q']*1 + ['Z']*1
    )
    
    # Example AI Rack
    ai_rack = ['A', 'Q', 'U', 'E', 'R', 'T', 'Y']
    
    # Generate 50 fake candidate moves that the AI might play
    mock_candidates = [
        Move(
            score=random.randint(15, 45), 
            heuristic_fitness=random.randint(10, 50), 
            tiles_played=[]
        ) 
        for _ in range(50)
    ]
    
    print(f"Starting Monte Carlo Simulation...")
    print(f"Total AI moves generated: {len(mock_candidates)}")
    print(f"Pre-filtering to top 15 heuristics...")
    print(f"Running 500 iterations per candidate (7,500 total game states)...")
    
    start_time = time.time()
    
    best_move, ev = get_best_move_monte_carlo(
        mock_candidates, 
        state, 
        ai_rack, 
        standard_distribution, 
        iterations=500
    )
    
    elapsed = time.time() - start_time
    
    print("\n--- RESULTS ---")
    print(f"Simulation completed in {elapsed:.3f} seconds.")
    if best_move is not None:
        print(f"Selected Move Base Score: {best_move.score}")
        print(f"Selected Move Expected Value (EV): {ev:.2f}")
    else:
        print("No valid moves found.")