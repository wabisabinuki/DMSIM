"""
対象クリーチャーに対して、ターン中などの期限付きパワー上昇修飾子を付与する効果。
"""

from effects.base.base_effect import (
    BaseEffect
)

from modifiers.power_modifier import (
    PowerModifier
)

from core.pending_cards import is_card_pending

from ui.card_display import format_card_name


class AddPowerModifierEffect(
    BaseEffect
):

    def __init__(
        self,
        target,
        amount,
    ):

        super().__init__()

        self.target = target

        self.amount = amount

    def resolve(self):

        if is_card_pending(self.target):
            return False

        original_power = self.target.get_current_power()

        modifier = PowerModifier(
            self.amount
        )

        self.target.power_modifiers.append(
            modifier
        )
        print(
            f"{format_card_name(self.target)} gets "
            f"{self.amount} power"
            f" (current power: {original_power} -> {self.target.get_current_power()})"
        )
