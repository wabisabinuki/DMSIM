"""
ReferenceScope: カード参照時のスコープ定義。
- CARD: カード全体の情報を参照（文明、カード全体タイプなど）
- FACE: 特定の面の情報を参照
- ACTIVE_FACE: 現在使用中の面の情報を参照
"""

from enum import Enum, auto


class ReferenceScope(Enum):
    """
    カード参照時のスコープを定義する。
    どのレベルの情報を参照しているかを明確化する。
    """
    CARD = auto()          # カード全体の情報（文明など）
    FACE = auto()          # 指定した面の情報
    ACTIVE_FACE = auto()   # 現在選択/使用中の面の情報
