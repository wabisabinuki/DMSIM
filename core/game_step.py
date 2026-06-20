"""
ゲームのターンステップ（アンタップ、ドロー、マナ、メイン、アタック、エンド）の定義クラス。
"""

# core/game_step.py

from enum import Enum, auto


class GameStep(Enum):
    """ターン内のメインステップ"""

    TURN_START = auto()
    DRAW = auto()
    MANA_CHARGE = auto()
    MAIN = auto()
    ATTACK = auto()
    TURN_END = auto()


class AttackSubStep(Enum):
    """攻撃ステップ内のサブステップ"""

    NONE = auto()
    DECLARE_ATTACKER = auto()
    DECLARE_BLOCKER = auto()
    BATTLE = auto()
    DIRECT_ATTACK = auto()
    ATTACK_END = auto()
