"""Continuous trait that stops matching creatures from attacking players."""

from abilities.active_condition import active_if_matches
from abilities.base.continuous_ability import ContinuousAbility
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.creature_scope import matches_creature_scope


class AttackPlayerLockAbility(ContinuousAbility):

    def __init__(
        self,
        game,
        active_if=None,
        scope="self",
        filter_spec=None,
    ):
        super().__init__()
        self.game = game
        self.active_if = active_if
        self.scope = scope
        self.filter_spec = filter_spec

    def forbids_attack_player(
        self,
        source,
        attacker,
    ):
        if not active_if_matches(
            self.active_if,
            source,
            self.game,
        ):
            return False

        if not matches_creature_scope(
            self.scope,
            source,
            attacker,
            owner=attacker.owner,
        ):
            return False

        return self._matches_filter(
            source,
            attacker,
        )

    def _matches_filter(
        self,
        source,
        attacker,
    ):
        if not self.filter_spec:
            return True

        return matches_card_filter_dsl_or_legacy(
            self.game,
            attacker,
            self.filter_spec,
            context={
                "source_card": source,
                "player": source.owner,
                "controller": source.owner,
            },
        )
