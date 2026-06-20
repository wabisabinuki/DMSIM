"""
クリーチャーが破壊された事実を通知するイベントクラス。
"""

from events.base_event import (
    BaseEvent
)

from ui.card_display import format_card_name


class DestroyEvent(BaseEvent):

    def __init__(
        self,
        card,
        player,
    ):

        super().__init__()

        self.card = card

        self.player = player

    def __str__(self):

        return (
            f"DestroyEvent("
            f"{format_card_name(self.card)} "
            f"owned by {self.player.name}"
            f")"
        )
