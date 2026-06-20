"""
攻撃ステップ全体の処理を締めくくり、攻撃後状態をクリーンアップするハンドラ。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)


class FinishAttackStepHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):
        pass
