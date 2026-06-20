"""Saber keyword replacement ability."""

from abilities.base.destroy_self_instead_ability import (
    DestroySelfInsteadAbility,
)
from core.card_filter_evaluator import CardFilterEvaluator
from core.pending_cards import is_card_pending
from events.destroy_attempt_event import DestroyAttemptEvent
from zones.zone_type import ZoneType


class SaberAbility(DestroySelfInsteadAbility):
    """Destroy this creature instead of a matching own creature."""

    confirm_prompt = "Use Saber?"

    def __init__(
        self,
        owner_card,
        game,
        filter_spec=None,
        optional=True,
    ):
        super().__init__(
            owner_card,
            game,
            optional=optional,
        )
        self.filter_spec = filter_spec or {}

    def applies(
        self,
        event,
    ):
        return (
            isinstance(event, DestroyAttemptEvent)
            and event.owner == self.owner_card.owner
            and event.card is not self.owner_card
            and self.owner_card.zone == ZoneType.BATTLE
            and not is_card_pending(self.owner_card)
            and self._matches(event.card)
        )

    def _matches(
        self,
        card,
    ):
        return CardFilterEvaluator(
            self.game
        ).matches(
            card,
            self.filter_spec,
            {
                "game": self.game,
                "player": self.owner_card.owner,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
            },
        )
