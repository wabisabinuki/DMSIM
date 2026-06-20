"""
領域の種類（DECK, HAND, SHIELD, MANA, BATTLE, GRAVEYARD, SUPER_DIMENSION）を定義する列挙型（Enum）。
"""

from enum import Enum, auto


class ZoneType(Enum):
    DECK = auto()
    HAND = auto()
    MANA = auto()
    BATTLE = auto()
    SHIELD = auto()
    GRAVEYARD = auto()
    SUPER_DIMENSION = auto()
