"""
lexicon.py - Dictionary loader and GADDAG initialization.
"""

import os
from typing import Optional, Set
from backend.gaddag import GADDAG

# Default path to dictionary relative to this file
DEFAULT_DICT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "dictionary.txt"
)

# In-memory cache for singleton access
_CACHED_GADDAG: Optional[GADDAG] = None
_CACHED_WORDS: Optional[Set[str]] = None


def load_dictionary(
    dict_path: str = DEFAULT_DICT_PATH,
    min_length: int = 2,
    max_length: int = 15
) -> GADDAG:
    """
    Loads words from a text file into a GADDAG graph structure.
    Only includes alphabetic words within [min_length, max_length].
    """
    if not os.path.exists(dict_path):
        raise FileNotFoundError(f"Dictionary file not found at: {dict_path}")

    dag = GADDAG()
    with open(dict_path, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().upper()
            if word.isalpha() and min_length <= len(word) <= max_length:
                dag.add_word(word)

    return dag


def get_dictionary_words(dict_path: str = DEFAULT_DICT_PATH) -> Set[str]:
    """
    Loads all words into a Python set for rapid O(1) membership validation.
    """
    global _CACHED_WORDS
    if _CACHED_WORDS is not None:
        return _CACHED_WORDS

    if not os.path.exists(dict_path):
        raise FileNotFoundError(f"Dictionary file not found at: {dict_path}")

    words = set()
    with open(dict_path, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().upper()
            if word.isalpha() and 2 <= len(word) <= 15:
                words.add(word)

    _CACHED_WORDS = words
    return words


def get_default_gaddag(dict_path: str = DEFAULT_DICT_PATH) -> GADDAG:
    """
    Returns a cached singleton GADDAG instance to avoid re-parsing on every call.
    """
    global _CACHED_GADDAG
    if _CACHED_GADDAG is None:
        _CACHED_GADDAG = load_dictionary(dict_path)
    return _CACHED_GADDAG

