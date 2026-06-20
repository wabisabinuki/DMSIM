"""Continuous trait that restricts how elements can enter battle."""

from abilities.base.continuous_ability import ContinuousAbility
from cards.card import ELEMENT_CARD_TYPES
from zones.zone_type import ZoneType


class ElementEntryLockAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        affected_player="opponent",
        allow_from_zone=None,
        allow_reason=None,
        allow_reasons=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.affected_player = affected_player
        self.allow_from_zone = self._zone(allow_from_zone)
        self.allow_reasons = set(allow_reasons or [])
        if allow_reason is not None:
            self.allow_reasons.add(allow_reason)

    def prevents_zone_change(
        self,
        event,
    ):
        return (
            self.owner_card.zone == ZoneType.BATTLE
            and event.to_zone == ZoneType.BATTLE
            and self._matches_player(event)
            and self._is_element(event.card)
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
            self.allow_from_zone is not None
            and event.from_zone == self.allow_from_zone
        ):
            return True

        if (
            self.allow_reasons
            and event.reason in self.allow_reasons
        ):
            return True

        return False

    def _is_element(
        self,
        card,
    ):
        return bool(
            set(getattr(card, "card_types", set()))
            & ELEMENT_CARD_TYPES
        )

    def _zone(
        self,
        zone,
    ):
        if zone is None:
            return None
        if isinstance(zone, ZoneType):
            return zone

        return ZoneType[
            str(zone)
            .replace("_zone", "")
            .replace(" ", "_")
            .upper()
        ]
