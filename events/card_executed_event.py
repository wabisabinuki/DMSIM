"""
城・クロスギアなど、召喚/キャスト以外のカード実行を通知するイベントクラス。
"""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class CardExecutedEvent(BaseEvent):

    def __init__(
        self,
        player,
        card,
        from_zone=None,
        ignore_cost=False,
        play_method=None,
    ):
        super().__init__()
        self.player = player
        self.card = card
        self.from_zone = from_zone
        self.ignore_cost = ignore_cost
        self.play_method = play_method
        self.cost_mode = play_method
        self.cost_skipped = bool(ignore_cost)

    def __str__(self):
        return (
            "CardExecutedEvent("
            f"{self.player.name} executes "
            f"{format_card_name(self.card)} "
            f"from {self._zone_name(self.from_zone)}"
            ")"
        )

    def _zone_name(
        self,
        zone,
    ):
        if zone is None:
            return "UNKNOWN"

        return zone.name
