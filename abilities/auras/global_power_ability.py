"""
他の味方クリーチャー全体のパワーを継続的に強化する全体パワー強化能力（GlobalPowerAbility）を定義。
"""

# abilities/global_power_ability.py

from abilities.base.continuous_ability import (
    ContinuousAbility
)


class GlobalPowerAbility(
    ContinuousAbility
):

    def __init__(
        self,
        amount,
    ):

        self.amount = amount

    def modify_power(
        self,
        creature,
        value,
    ):

        return (
            value + self.amount
        )
