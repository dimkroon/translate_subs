"""
User-Agents\n
A Python module which does one thing: giving you a random User-Agent Header

Anime no Sekai - 2021
"""

from sys import version_info
if version_info < (3, 0):
    from ._backward_compatibility import random
else:
    from ._useragents import random

__author__      = 'Anime no Sekai'
__copyright__   = 'Copyright 2021, translate'
__credits__     = ['animenosekai']
__license__     = 'MIT'
__version__     = 'pyuseragents v1.0.5'
__maintainer__  = 'Anime no Sekai'
__email__       = 'niichannomail@gmail.com'
__status__      = 'Stable'
