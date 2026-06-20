"""
攻撃宣言後の防衛側ブロック宣言ステップなど、攻撃中フェーズの遷移を進めるハンドラ。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)


class ProceedToAttackStepHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):
        pass
