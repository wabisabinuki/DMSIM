"""Continuous trait that stops creatures from attacking the turn they enter.

The set of affected creatures is controlled by ``scope`` (own / opponent /
all) and an optional ``filter`` card-filter DSL spec so card text such as
"出たターン、相手のパワー5000以上のクリーチャーは攻撃できない" can be
expressed from JSON.
"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.active_condition import active_if_matches
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.creature_scope import matches_creature_scope


class EnterTurnAttackLockAbility(ContinuousAbility):

    def __init__(
        self,
        game,
        active_if=None,
        scope="opponent_creatures",
        filter_spec=None,
    ):
        super().__init__()
        self.game = game
        self.active_if = active_if
        self.scope = scope
        self.filter_spec = filter_spec

    def is_active_for(
        self,
        source,
    ):
        return active_if_matches(
            self.active_if,
            source,
            self.game,
        )

    def forbids_attack(
        self,
        source,
        attacker,
    ):
        if not self.is_active_for(source):
            return False

        if not matches_creature_scope(
            self.scope,
            source,
            attacker,
            owner=attacker.owner,
        ):
            return False

        if not self._matches_filter(source, attacker):
            return False

        return (
            getattr(
                attacker,
                "summon_turn",
                None,
            )
            == self.game.state.turn
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
