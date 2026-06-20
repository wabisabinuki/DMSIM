"""
CardFace: ツインパクトカードの各面情報を保持するクラス。
クリーチャー面またはスペル面の情報を独立して管理します。
"""

from enum import Enum, auto
from typing import List, Optional


class FaceType(Enum):
    """面の種類"""
    CREATURE = auto()
    SPELL = auto()


class CardFace:
    """
    カード1面分の情報を保持。
    - 面のタイプ（クリーチャー/呪文）
    - コスト
    - 文明
    - 能力
    - クリーチャー固有：パワー、日本語種族
    """

    def __init__(
        self,
        face_type: FaceType,
        cost: int,
        civilization: int,
        abilities: Optional[List] = None,
        power: Optional[int] = None,
        race_ja: Optional[str] = None,
    ):
        self.face_type = face_type
        self.cost = cost
        self.civilization = civilization
        self.abilities = abilities or []
        self.power = power  # クリーチャー側のみ
        self.race_ja = race_ja    # クリーチャー側のみ

    def is_creature(self) -> bool:
        return self.face_type == FaceType.CREATURE

    def is_spell(self) -> bool:
        return self.face_type == FaceType.SPELL

    def __str__(self):
        face_name = "Creature" if self.is_creature() else "Spell"
        return f"{face_name} Face (Cost: {self.cost})"
