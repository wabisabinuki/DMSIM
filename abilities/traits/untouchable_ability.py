"""Convenience trait for creatures opponents cannot choose."""

from abilities.base.continuous_ability import (
    ContinuousAbility,
)


class UntouchableAbility(ContinuousAbility):

    def can_be_chosen_by(
        self,
        source_player,
        creature,
    ):

        return source_player == creature.owner
