"""
This version doesn't have any type annotations and supports Python 2
Anime no Sekai 2021

"""

from random import randint
from .data.list import USER_AGENTS

def random():
    """
    Returns a new random User-Agent Header value    
    Args:
        None
    Returns:
        str
    """
    if len(USER_AGENTS) > 0:
        return USER_AGENTS[randint(0, len(USER_AGENTS) - 1)]
    else: # first element of the default list
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
