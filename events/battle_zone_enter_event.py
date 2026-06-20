"""
カードがバトルゾーンに出た事実を通知するイベントクラス。
"""

from events.base_event import BaseEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class BattleZoneEnterEvent(BaseEvent):

    def __init__(
        self,
        player,
        card,
        from_zone,
        reason=None,
        cost_skipped=False,
    ):
        super().__init__()

        self.player = player
        self.owner = player
        self.card = card
        self.from_zone = from_zone
        self.to_zone = ZoneType.BATTLE
        self.reason = reason
        self.entered_by_summon = reason == "summon"
        self.cost_skipped = bool(cost_skipped or reason != "summon")
        self.ignore_cost = self.cost_skipped

    def __str__(self):

        return (
            f"BattleZoneEnterEvent("
            f"{format_card_name(self.card)}: "
            f"{self.from_zone.name} -> BATTLE, "
            f"reason={self.reason}"
            f")"
        )
