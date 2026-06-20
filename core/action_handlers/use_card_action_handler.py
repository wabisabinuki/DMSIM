"""
手札からカードを使用する基本ハンドラ。クリーチャーなら召喚、呪文ならキャストを呼び出します。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)


class UseCardActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        action.card.use(
            self.game_controller,
            action.player,
            ignore_cost=(
                action.ignore_cost
            ),
        )
