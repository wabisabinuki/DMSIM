"""
ブロッカー能力を定義するクラス。相手の攻撃時に自身をタップして攻撃対象を移し替えます。
"""

from abilities.base.continuous_ability import (
    ContinuousAbility
)
from abilities.active_condition import active_if_matches


class BlockerAbility(
    ContinuousAbility
):

    def __init__(
        self,
        active_if=None,
    ):
        super().__init__()
        self.active_if = active_if

    def is_active_for(
        self,
        creature,
    ):
        return active_if_matches(
            self.active_if,
            creature,
            None,
        )
