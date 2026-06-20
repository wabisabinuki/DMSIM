"""
クリーチャーの召喚が呼び出された事実を通知するイベントクラス。
"""

from events.base_event import BaseEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class SummonEvent(BaseEvent):

    def __init__(
        self,
        player,
        card,
        from_zone=None,
        evolution_source=None,
        ignore_cost=False,
        play_method=None,
    ):
        super().__init__()

        self.player = player
        self.card = card
        self.from_zone = from_zone
        self.to_zone = ZoneType.BATTLE
        self.evolution_source = evolution_source
        self.ignore_cost = ignore_cost
        self.play_method = play_method
        self.cost_mode = play_method
        self.cost_skipped = bool(ignore_cost)

    def __str__(self):

        return (
            f"SummonEvent("
            f"{self.player.name} calls "
            f"{format_card_name(self.card)} "
            f"from {self._zone_name(self.from_zone)} "
            f"to BATTLE"
            f")"
        )

    def _zone_name(
        self,
        zone,
    ):

        if zone is None:
            return "UNKNOWN"

        return zone.name
