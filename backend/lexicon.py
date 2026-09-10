"""
lexicon.py - Dictionary loader and GADDAG initialization for Scrabble lexicons.
Supports both NASPA (NWL23) and CSW24 (Collins Scrabble Words 2024).
"""

import os
from typing import Optional, Set, Dict, Tuple
try:
    from backend.gaddag import GADDAG
except ImportError:
    from gaddag import GADDAG

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

LEXICON_PATHS: Dict[str, str] = {
    "NASPA": os.path.join(DATA_DIR, "naspa.txt"),
    "CSW24": os.path.join(DATA_DIR, "csw24.txt"),
}

LEXICON_DESCRIPTIONS: Dict[str, str] = {
    "NASPA": "NASPA Word List (North American - NWL23, 196k words)",
    "CSW24": "Collins Scrabble Words 2024 (International - WESPA, 279k words)",
}

DEFAULT_LEXICON = "NASPA"

# In-memory cache for singleton access per lexicon
_CACHED_GADDAGS: Dict[str, GADDAG] = {}
_CACHED_WORDS: Dict[str, Set[str]] = {}


def resolve_lexicon(lexicon_or_path: str = DEFAULT_LEXICON) -> Tuple[str, str]:
    """
    Resolves a lexicon name or file path into (canonical_name, file_path).
    Supports 'NASPA', 'NWL', 'CSW24', 'CSW', 'COLLINS' or direct file paths.
    """
    key = lexicon_or_path.strip().upper()
    if key in ("NASPA", "NWL", "NWL2023", "NWL23", "TWL"):
        return "NASPA", LEXICON_PATHS["NASPA"]
    elif key in ("CSW24", "CSW", "CSW21", "COLLINS", "SOWPODS", "INTERNATIONAL"):
        return "CSW24", LEXICON_PATHS["CSW24"]

    # Check if a custom file path was passed
    if os.path.exists(lexicon_or_path):
        canonical = os.path.basename(lexicon_or_path).split(".")[0].upper()
        return canonical, os.path.abspath(lexicon_or_path)

    if "/" in lexicon_or_path or "\\" in lexicon_or_path or lexicon_or_path.endswith(".txt"):
        raise FileNotFoundError(f"Dictionary file not found at: {lexicon_or_path}")

    # Fallback to default
    return "NASPA", LEXICON_PATHS["NASPA"]


def load_dictionary(
    lexicon_or_path: str = DEFAULT_LEXICON,
    min_length: int = 2,
    max_length: int = 15
) -> GADDAG:
    """
    Loads words from the specified lexicon file into a GADDAG graph structure.
    Only includes alphabetic words within [min_length, max_length].
    """
    name, dict_path = resolve_lexicon(lexicon_or_path)

    if not os.path.exists(dict_path):
        raise FileNotFoundError(f"Dictionary file not found at: {dict_path}")

    dag = GADDAG()
    with open(dict_path, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().upper()
            if word.isalpha() and min_length <= len(word) <= max_length:
                dag.add_word(word)

    return dag


def get_dictionary_words(lexicon_or_path: str = DEFAULT_LEXICON) -> Set[str]:
    """
    Loads all words from the specified lexicon into a set for rapid O(1) membership validation.
    """
    name, dict_path = resolve_lexicon(lexicon_or_path)

    if name in _CACHED_WORDS:
        return _CACHED_WORDS[name]

    if not os.path.exists(dict_path):
        raise FileNotFoundError(f"Dictionary file not found at: {dict_path}")

    words = set()
    with open(dict_path, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().upper()
            if word.isalpha() and 2 <= len(word) <= 15:
                words.add(word)

    _CACHED_WORDS[name] = words
    return words


def get_default_gaddag(lexicon_or_path: str = DEFAULT_LEXICON) -> GADDAG:
    """
    Returns a cached singleton GADDAG instance for the requested lexicon
    to avoid re-parsing the text file on every call.
    """
    name, _ = resolve_lexicon(lexicon_or_path)
    if name not in _CACHED_GADDAGS:
        _CACHED_GADDAGS[name] = load_dictionary(name)
    return _CACHED_GADDAGS[name]
