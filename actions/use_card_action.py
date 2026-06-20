"""
手札からカード（クリーチャーまたは呪文）を使用する一般的なアクションのデータを保持するクラス。
"""

from ui.card_display import format_card_name
from actions.play_method import (
    ignores_mana_cost,
    normalize_play_method,
)


class UseCardAction:

    def __init__(
        self,
        player,
        card,
        ignore_cost=False,
        play_method=None,
        cost_mode=None,
        play_permission=None,
    ):

        self.player = player
        self.card = card
        self.play_method = normalize_play_method(
            play_method
            if play_method is not None
            else cost_mode,
            ignore_cost=ignore_cost,
        )
        self.cost_mode = self.play_method
        self.ignore_cost = (
            bool(ignore_cost)
            or ignores_mana_cost(self.play_method)
        )
        self.play_permission = play_permission

    def __str__(self):

        return (
            f"Use {format_card_name(self.card)}"
        )
