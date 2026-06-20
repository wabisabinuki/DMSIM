"""
ターン終了アクションを実行するハンドラ。ターン終了イベントを発行し、ターン進行を終了します。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)


class EndTurnActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        self.game_controller\
            .presenter\
            .on_turn_end_board(
                self.game_controller.state
            )

        self.game_controller\
            .turn_manager\
            .advance_turn()
