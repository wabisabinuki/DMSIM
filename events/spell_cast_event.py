"""Event published when a spell is cast."""

from events.base_event import BaseEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class SpellCastEvent(BaseEvent):

    def __init__(
        self,
        player,
        spell,
        from_zone=None,
        ignore_cost=False,
        play_method=None,
    ):
        super().__init__()
        self.player = player
        self.spell = spell
        self.card = spell
        self.from_zone = from_zone
        self.to_zone = ZoneType.GRAVEYARD
        self.ignore_cost = ignore_cost
        self.play_method = play_method
        self.cost_mode = play_method
        self.cost_skipped = bool(ignore_cost)

    def __str__(self):
        return (
            "SpellCastEvent("
            f"{self.player.name} casts "
            f"{format_card_name(self.spell)} "
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
