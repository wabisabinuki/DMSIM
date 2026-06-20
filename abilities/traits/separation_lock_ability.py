"""Continuous ability that prevents creatures from leaving battle."""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.active_condition import active_if_matches
from core.creature_scope import matches_creature_scope
from effects.composition.card_predicates import is_creature_card
from zones.zone_type import ZoneType


class SeparationLockAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        active_if=None,
        scope="own_creatures",
        target_card=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.active_if = active_if
        self.scope = scope
        self.target_card = target_card

    def prevents_zone_change(
        self,
        event,
    ):
        return (
            self._is_active()
            and event.from_zone == ZoneType.BATTLE
            and event.to_zone != ZoneType.BATTLE
            and self._matches_scope(event)
        )

    def _matches_scope(
        self,
        event,
    ):
        card = event.card

        if not is_creature_card(card):
            return False

        return matches_creature_scope(
            self.scope,
            self.owner_card,
            card,
            owner=event.owner,
            target_card=self.target_card,
        )

    def _is_active(
        self,
    ):
        if self.active_if is None:
            return True

        if self.active_if == "hyper_mode":
            return active_if_matches(
                self.active_if,
                self.owner_card,
                None,
            )

        if isinstance(self.active_if, dict):
            return active_if_matches(
                self.active_if,
                self.owner_card,
                None,
            )

        is_grant_active = getattr(
            self.active_if,
            "is_grant_active",
            None,
        )
        if is_grant_active is not None:
            return is_grant_active()

        return bool(self.active_if)
