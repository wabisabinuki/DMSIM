"""Continuous trait that restricts which zones creatures may enter battle from.

Two complementary modes are supported so card text variations can be
expressed from JSON:

- allow-list (``allow_from_zones``): creatures may *only* enter from the
  listed zones (e.g. "出るのは手札か山札からのみ").
- block-list (``block_from_zones``): creatures may enter from any zone
  *except* the listed ones (e.g. "墓地からは出ない").
"""

from abilities.base.continuous_ability import ContinuousAbility
from cards.card import CardType
from zones.zone_type import ZoneType


class CreatureEntryLockAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        affected_player="opponent",
        allow_from_zones=None,
        block_from_zones=None,
        allow_reasons=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.affected_player = affected_player
        self.allow_from_zones = self._zones(allow_from_zones)
        self.block_from_zones = self._zones(block_from_zones)
        self.allow_reasons = set(allow_reasons or [])

    def prevents_zone_change(
        self,
        event,
    ):
        return (
            self.owner_card.zone == ZoneType.BATTLE
            and event.to_zone == ZoneType.BATTLE
            and self._matches_player(event)
            and self._is_creature(event.card)
            and not self._is_allowed(event)
        )

    def _matches_player(
        self,
        event,
    ):
        if self.affected_player == "opponent":
            return event.owner != self.owner_card.owner
        if self.affected_player == "own":
            return event.owner == self.owner_card.owner
        return True

    def _is_allowed(
        self,
        event,
    ):
        if (
            self.allow_reasons
            and event.reason in self.allow_reasons
        ):
            return True

        if self.block_from_zones:
            return event.from_zone not in self.block_from_zones

        if self.allow_from_zones:
            return event.from_zone in self.allow_from_zones

        # 制限指定が無ければ何も妨げない（安全側のデフォルト）。
        return True

    def _is_creature(
        self,
        card,
    ):
        return CardType.CREATURE in getattr(
            card,
            "card_types",
            set(),
        )

    def _zones(
        self,
        zones,
    ):
        if zones is None:
            return frozenset()

        if isinstance(zones, (str, ZoneType)):
            zones = [zones]

        return frozenset(
            self._zone(zone)
            for zone in zones
            if zone is not None
        )

    def _zone(
        self,
        zone,
    ):
        if isinstance(zone, ZoneType):
            return zone

        return ZoneType[
            str(zone)
            .replace("_zone", "")
            .replace(" ", "_")
            .upper()
        ]
