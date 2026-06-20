"""
相手クリーチャーに対する攻撃アクションを実行するハンドラ。戦闘マネージャを呼び出してバトルを処理します。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)


class AttackCreatureActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        self.game_controller\
            .combat_manager\
            .process_battle(
                action
            )
