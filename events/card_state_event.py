"""Events for tap and untap state changes."""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class CardTappedEvent(BaseEvent):

    def __init__(
        self,
        player,
        card,
        reason=None,
    ):
        super().__init__()
        self.player = player
        self.card = card
        self.reason = reason

    def __str__(self):
        return (
            "CardTappedEvent("
            f"{format_card_name(self.card)}"
            ")"
        )


class CardUntappedEvent(BaseEvent):

    def __init__(
        self,
        player,
        card,
        reason=None,
    ):
        super().__init__()
        self.player = player
        self.card = card
        self.reason = reason

    def __str__(self):
        return (
            "CardUntappedEvent("
            f"{format_card_name(self.card)}"
            ")"
        )
