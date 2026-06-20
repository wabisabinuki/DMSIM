"""Continuous ability that makes affected cards enter zones tapped."""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.active_condition import active_if_matches
from zones.zone_type import ZoneType


ZONE_ALIASES = {
    "battle": ZoneType.BATTLE,
    "battle_zone": ZoneType.BATTLE,
    "mana": ZoneType.MANA,
    "mana_zone": ZoneType.MANA,
}


class TapToPlayAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        affected_player="opponent",
        zones=None,
        active_if=None,
        tap_required=True,
        optional=False,
        prompt=None,
        game=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.affected_player = affected_player
        self.zones = tuple(
            self._zone(zone)
            for zone in (
                zones
                or (
                    "mana_zone",
                    "battle_zone",
                )
            )
        )
        self.active_if = active_if
        self.tap_required = bool(tap_required)
        self.optional = bool(optional)
        self.prompt = (
            prompt
            or "Enter the battle zone tapped?"
        )
        self.game = game

    def after_zone_change(
        self,
        event,
    ):
        if (
            not self.tap_required
            or not self._is_active()
            or event.to_zone not in self.zones
            or not self._affects(event)
        ):
            return

        if (
            self.optional
            and not self._confirm()
        ):
            return

        event.card.tapped = True

    def _confirm(
        self,
    ):
        if self.game is None:
            return True

        return bool(
            self.game.choice_manager.select(
                self.owner_card.owner,
                [
                    True,
                    False,
                ],
                prompt=self.prompt,
            )
        )

    def _is_active(
        self,
    ):
        return active_if_matches(
            self.active_if,
            self.owner_card,
            None,
        )

    def _affects(
        self,
        event,
    ):
        if self.affected_player == "self":
            return event.card is self.owner_card

        player = event.owner
        if self.affected_player == "opponent":
            return player != self.owner_card.owner
        if self.affected_player == "controller":
            return player == self.owner_card.owner
        if self.affected_player == "all":
            return True

        return False

    def _zone(
        self,
        value,
    ):
        if isinstance(
            value,
            ZoneType,
        ):
            return value

        key = str(value).lower()
        if key not in ZONE_ALIASES:
            raise ValueError(f"Unknown tap_to_play zone: {value}")

        return ZONE_ALIASES[key]
