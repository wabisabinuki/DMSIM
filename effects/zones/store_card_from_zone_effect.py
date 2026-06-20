"""Store a visible card from a zone without moving it."""

from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.pending_cards import visible_cards
from effects.base.base_effect import BaseEffect
from effects.zones.zone_effect_utils import (
    default_selection_for_zone,
    parse_zone,
    resolve_player,
)
from zones.zone_type import ZoneType


class StoreCardFromZoneEffect(BaseEffect):
    """Save a selected card into package_context for later effects."""

    def __init__(
        self,
        player,
        game,
        from_zone,
        store_as,
        target_player="self",
        filter_spec=None,
        selection=None,
        optional=False,
        prompt=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.from_zone = parse_zone(from_zone)
        self.store_as = store_as
        self.target_player = target_player
        self.filter_spec = filter_spec or {}
        self.selection = selection or default_selection_for_zone(
            self.from_zone
        )
        self.optional = optional
        self.prompt = prompt or f"Choose a card from {self.from_zone.name}"
        self._validate()

    def can_attempt(self):
        owner = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return False

        return bool(self._candidate_cards(owner))

    def resolve(self):
        owner = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return False

        card = self._select_card(owner)
        if card is None:
            return False

        self.package_context[self.store_as] = card
        return True

    def _select_card(
        self,
        owner,
    ):
        candidates = self._candidate_cards(owner)
        if not candidates:
            return None

        if self.selection == "top":
            return candidates[0]

        if self.selection == "bottom":
            return candidates[-1]

        if self.selection == "first_matching":
            return candidates[0]

        if self.selection == "choose":
            return self.game.target_selector.select(
                self.player,
                candidates,
                prompt=self.prompt,
                can_skip=self.optional,
            )

        raise ValueError(
            f"Unknown store selection: {self.selection}"
        )

    def _candidate_cards(
        self,
        owner,
    ):
        cards = self._visible_source_cards(owner)
        if not cards:
            return []

        if self.selection == "top":
            card = cards[0]
            return [card] if self._matches(card) else []

        if self.selection == "bottom":
            card = cards[-1]
            return [card] if self._matches(card) else []

        return [
            card
            for card in cards
            if self._matches(card)
        ]

    def _visible_source_cards(
        self,
        owner,
    ):
        if self.from_zone == ZoneType.SHIELD:
            visible_shields = getattr(
                owner.shield_zone,
                "visible_shields",
                None,
            )
            if visible_shields is not None:
                return visible_shields()

        return visible_cards(
            owner.get_zone(self.from_zone).cards
        )

    def _matches(
        self,
        card,
    ):
        return matches_card_filter_dsl_or_legacy(
            self.game,
            card,
            self.filter_spec,
            context={
                **self.package_context,
                "player": self.player,
                "controller": self.player,
                "source_card": self.source_card,
            },
        )

    def _validate(self):
        if not self.store_as:
            raise ValueError("store_card_from_zone requires store_as")

        if self.selection not in (
            "bottom",
            "choose",
            "first_matching",
            "top",
        ):
            raise ValueError(
                f"Unknown store selection: {self.selection}"
            )
