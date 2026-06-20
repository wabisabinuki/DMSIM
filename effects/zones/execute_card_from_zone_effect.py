"""Execute a matching card from a configurable zone."""

from cards.card import Card
from cards.twin_pact_card import TwinPactCard
from effects.base.base_effect import BaseEffect
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.zones.zone_effect_utils import (
    default_selection_for_zone,
    merge_filter_spec,
    parse_zone,
    resolve_player,
)
from core.pending_cards import visible_cards


class ExecuteCardFromZoneEffect(BaseEffect):

    def __init__(
        self,
        player,
        game,
        from_zone="hand",
        card_type="element",
        filter_spec=None,
        optional=True,
        prompt=None,
        ignore_cost=True,
        target_player="self",
        selection=None,
        max_cost=None,
        store_as=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.from_zone = parse_zone(from_zone)
        self.card_type = card_type
        filter_spec = dict(filter_spec or {})
        if max_cost is not None:
            filter_spec.setdefault(
                "max_cost",
                max_cost,
            )
        self.store_as = store_as
        self.filter_spec = merge_filter_spec(
            {
                "type": card_type,
            }
            if card_type is not None
            else {},
            filter_spec,
        )
        self.optional = optional
        self.prompt = (
            prompt
            or "Choose a card to execute"
        )
        self.ignore_cost = ignore_cost
        self.target_player = target_player
        self.selection = (
            selection
            or default_selection_for_zone(self.from_zone)
        )

    def can_attempt(self):
        owner = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return False

        if self.selection == "choose":
            return bool(self._candidates(owner))

        if self.selection == "top":
            cards = self._source_cards(owner)
            return bool(cards) and self._matches(
                cards[0],
                owner,
            )

        if self.selection == "bottom":
            cards = self._source_cards(owner)
            return bool(cards) and self._matches(
                cards[-1],
                owner,
            )

        if self.selection == "first_matching":
            return bool(self._candidates(owner))

        raise ValueError(
            f"Unknown execution selection: {self.selection}"
        )

    def resolve(self):
        owner = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return False

        if (
            self.optional
            and self.selection != "choose"
            and not self._confirm(owner)
        ):
            return False

        card = self._select_card(owner)
        if card is None:
            return False

        self._prepare_card_for_execution(card)
        before_zone = getattr(
            card,
            "zone",
            None,
        )
        before_counter = getattr(
            card,
            "zone_change_counter",
            None,
        )

        card.use(
            self.game,
            owner,
            ignore_cost=self.ignore_cost,
        )

        if self.store_as:
            self.package_context[self.store_as] = card

        return (
            getattr(
                card,
                "zone",
                None,
            )
            != before_zone
            or getattr(
                card,
                "zone_change_counter",
                None,
            )
            != before_counter
        )

    def _select_card(
        self,
        owner,
    ):
        if self.selection == "choose":
            options = self._candidates(owner)
            if not options:
                return None

            return self.game.target_selector.select(
                self.player,
                options=options,
                prompt=self.prompt,
                can_skip=self.optional,
            )

        if self.selection == "top":
            cards = self._source_cards(owner)
            if not cards:
                return None

            card = cards[0]
            return (
                card
                if self._matches(card, owner)
                else None
            )

        if self.selection == "bottom":
            cards = self._source_cards(owner)
            if not cards:
                return None

            card = cards[-1]
            return (
                card
                if self._matches(card, owner)
                else None
            )

        if self.selection == "first_matching":
            options = self._candidates(owner)
            return options[0] if options else None

        raise ValueError(
            f"Unknown execution selection: {self.selection}"
        )

    def _candidates(
        self,
        owner=None,
    ):
        owner = owner or resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return []

        return [
            card
            for card in self._source_cards(owner)
            if self._matches(
                card,
                owner,
            )
        ]

    def _source_cards(
        self,
        owner,
    ):
        return visible_cards(
            owner.get_zone(
                self.from_zone
            ).cards
        )

    def _matches(
        self,
        card,
        owner,
    ):
        return (
            self._is_executable(card)
            and matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.filter_spec,
                context={
                    **self.package_context,
                    "player": owner,
                },
                usage_type=self.card_type,
            )
            and self._can_pay_if_needed(
                card,
                owner,
            )
        )

    def _is_executable(
        self,
        card,
    ):
        return type(card).use is not Card.use

    def _can_pay_if_needed(
        self,
        card,
        owner,
    ):
        if self.ignore_cost:
            return True

        selected_face = getattr(
            card,
            "selected_face",
            None,
        )
        self._prepare_card_for_execution(card)
        try:
            return owner.can_play(card)
        finally:
            if isinstance(
                card,
                TwinPactCard,
            ):
                card.selected_face = selected_face
                card._bind_selected_face_abilities()

    def _prepare_card_for_execution(
        self,
        card,
    ):
        if not isinstance(
            card,
            TwinPactCard,
        ):
            return

        key = (
            str(self.card_type).lower()
            if self.card_type is not None
            else None
        )
        if key in (
            "element",
            "creature",
        ):
            card.select_creature_face()
            return

        if key in (
            "non_creature",
            "spell",
        ):
            card.select_spell_face()

    def _confirm(
        self,
        owner,
    ):
        if not self._candidates(owner):
            return False

        return self.game.choice_manager.select(
            self.player,
            [
                True,
                False,
            ],
            prompt=self.prompt,
        )
