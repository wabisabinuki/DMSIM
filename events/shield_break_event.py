"""
シールドがブレイクされた事実を通知するイベントクラス。ブレイクされたシールドを保持します。
"""

from events.base_event import (
    BaseEvent
)

from ui.card_display import format_card_name


class ShieldBreakEvent(
    BaseEvent
):

    def __init__(
        self,
        player,
        shield_card,
        breaker,
    ):

        super().__init__()

        self.player = player

        self.shield_card = shield_card

        self.breaker = breaker

    def __str__(self):

        return (
            f"ShieldBreakEvent("
            f"{self.shield_card.name} "
            f"owned by {self.player.name} "
            f"broken by {format_card_name(self.breaker)}"
            f")"
        )
