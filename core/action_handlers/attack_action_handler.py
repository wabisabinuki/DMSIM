"""
プレイヤーやシールドに対する攻撃アクションを実行するハンドラ。攻撃イベントの発行、シールドブレイク、ダイレクトアタック判定を処理します。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)


class AttackActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        self.game_controller\
            .combat_manager\
            .process_attack(
                action
            )
