"""Timing just before choosing how many shields to break."""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class ShieldBreakChoiceEvent(BaseEvent):

    def __init__(
        self,
        attacker,
        target_player,
        break_options,
    ):

        super().__init__()
        self.attacker = attacker
        self.target_player = target_player
        self.break_options = tuple(
            break_options
        )

    def __str__(
        self,
    ):

        return (
            "ShieldBreakChoiceEvent("
            f"{format_card_name(self.attacker)} "
            f"chooses from {list(self.break_options)} "
            f"against {self.target_player.name}"
            ")"
        )
