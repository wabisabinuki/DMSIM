"""Continuous trait that makes opposing creatures attack if able."""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.active_condition import active_if_matches
from core.creature_scope import matches_creature_scope


class OpponentAttackMandatoryAbility(ContinuousAbility):

    def __init__(
        self,
        active_if=None,
        scope="opponent_creatures",
    ):
        super().__init__()
        self.active_if = active_if
        self.scope = scope

    def is_active_for(
        self,
        source,
    ):
        return active_if_matches(
            self.active_if,
            source,
            None,
        )

    def requires_attack(
        self,
        source,
        attacker,
    ):
        return (
            self.is_active_for(source)
            and matches_creature_scope(
                self.scope,
                source,
                attacker,
                owner=attacker.owner,
            )
        )
