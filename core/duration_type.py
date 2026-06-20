"""
期間のある効果の期間タイプを定義するenum。
"""

from enum import Enum


class DurationType(Enum):
    """
    効果の有効期間を定義するタイプ。
    """

    UNTIL_END_OF_TURN = "until_end_of_turn"
    """このターン終わりまで"""

    UNTIL_END_OF_OPPONENT_TURN = "until_end_of_opponent_turn"
    """次の相手ターン終わりまで"""

    UNTIL_END_OF_X_TURNS = "until_end_of_x_turns"
    """指定ターン数の終わりまで"""

    UNTIL_START_OF_CONTROLLER_TURN = "until_start_of_controller_turn"
    """次の自分のターンのはじめまで"""

    PERMANENT = "permanent"
    """永続（期間終了しない）。クリーチャーへの恒常的な能力付与などに使う。"""

    def __str__(self):
        return self.value
