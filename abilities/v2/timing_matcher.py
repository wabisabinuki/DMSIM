"""Activation timing matching for v2 activated ability specs."""

from core.game_step import GameStep
from zones.zone_type import ZoneType


ZONE_NAMES = {
    "battle": ZoneType.BATTLE,
    "battle_zone": ZoneType.BATTLE,
    "graveyard": ZoneType.GRAVEYARD,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "shield": ZoneType.SHIELD,
}

STEP_NAMES = {
    "attack": GameStep.ATTACK,
    "main": GameStep.MAIN,
}


class ActivationTimingMatcher:
    """Evaluate activated ability timing specs."""

    MATCHERS = {
        "active_zone": "_match_active_zone",
        "active_zones": "_match_active_zone",
        "step": "_match_step",
    }

    def __init__(
        self,
        game,
        owner_card,
        timing,
    ):
        self.game = game
        self.owner_card = owner_card
        self.timing = timing or {}

    def matches(
        self,
    ):
        return all(
            getattr(self, handler_name)(self.timing[key])
            for key, handler_name in self.MATCHERS.items()
            if key in self.timing
        )

    def active_zones(
        self,
    ):
        return self._zones(
            self.timing.get(
                "active_zones",
                self.timing.get("active_zone", "battle"),
            )
        )

    def _match_active_zone(
        self,
        value,
    ):
        zones = self._zones(value)
        return (
            not zones
            or getattr(
                self.owner_card,
                "zone",
                None,
            )
            in zones
        )

    def _match_step(
        self,
        value,
    ):
        return self.game.state.step == STEP_NAMES[value]

    def _zones(
        self,
        value,
    ):
        if value == "any":
            return []

        if isinstance(
            value,
            str,
        ):
            value = [
                value,
            ]

        return [
            ZONE_NAMES[zone]
            for zone in value
        ]
