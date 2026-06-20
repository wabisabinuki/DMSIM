"""Convenience trait for creatures that cannot be blocked."""

from abilities.base.continuous_ability import (
    ContinuousAbility,
)


class UnblockableAbility(ContinuousAbility):
    """このクリーチャーはブロックされない能力。

    ``condition`` を指定すると、特定のブロッカーに対してのみ
    ブロック不可となる「条件付きブロックされない」を表現できる。
    """

    def __init__(self, condition=None):
        super().__init__()
        self.condition = condition

    def is_unconditional(self):
        """常にブロックされない（相手を選ばない）能力なら True。"""
        return self.condition is None

    def blocks_blocker(self, attacker, blocker):
        """この能力により ``attacker`` が ``blocker`` にブロックされないなら True。"""

        if self.condition is None:
            return True

        if self.condition == "blocker_power_less_than_self":
            return (
                blocker.get_current_power()
                < attacker.get_current_power()
            )

        return False
