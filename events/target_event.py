"""Events for card target selection."""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class CardChosenEvent(BaseEvent):

    def __init__(
        self,
        player,
        card,
        prompt=None,
    ):
        super().__init__()
        self.player = player
        self.card = card
        self.prompt = prompt

    def __str__(self):
        return (
            "CardChosenEvent("
            f"{self.player.name} chose "
            f"{format_card_name(self.card)}"
            ")"
        )
