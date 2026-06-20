"""Attempt event for replacing a shield break."""

from events.base_event import BaseEvent


class ShieldBreakAttemptEvent(BaseEvent):

    def __init__(
        self,
        player,
        shield_card,
        breaker,
        shield_cards=None,
    ):

        super().__init__()
        self.player = player
        self.owner = player
        self.shield_card = shield_card
        self.shield_cards = (
            list(shield_cards)
            if shield_cards is not None
            else [shield_card]
        )
        self.card = shield_card
        self.breaker = breaker
        self.replaced = False
        self.cancelled = False
