"""Generic card movement effect for JSON card definitions."""

from effects.base.base_effect import BaseEffect
from effects.amount_choice import resolve_effect_amount
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.zones.zone_effect_utils import (
    default_selection_for_zone,
    parse_zone,
    resolve_player,
)
from core.pending_cards import visible_cards
from zones.zone_type import ZoneType


class MoveCardEffect(BaseEffect):

    DEFAULT_FACE_OPTIONS = (
        "face_down",
    )

    def __init__(
        self,
        player,
        game,
        from_zone,
        to_zone,
        amount=1,
        min_amount=None,
        max_amount=None,
        target_player="self",
        filter_spec=None,
        selection=None,
        optional=True,
        prompt=None,
        tapped=None,
        face_options=None,
        shield_face=None,
        destination_position=None,
        store_as=None,
        reason=None,
        evolution_mode="stack",
        shield_placement="new",
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.from_zone = parse_zone(from_zone)
        self.to_zone = parse_zone(to_zone)
        self.amount = amount
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.target_player = target_player
        self.filter_spec = filter_spec or {}
        self.selection = (
            selection
            or default_selection_for_zone(self.from_zone)
        )
        self.optional = optional
        self.prompt = (
            prompt
            or f"Choose a card from {self.from_zone.name}"
        )
        self.tapped = tapped
        self.face_options = tuple(
            face_options
            or (
                (shield_face,)
                if shield_face is not None
                else self.DEFAULT_FACE_OPTIONS
            )
        )
        self.destination_position = destination_position
        self.store_as = store_as
        self.reason = reason or "move_card"
        self.evolution_mode = evolution_mode
        self.shield_placement = shield_placement or "new"
        self._validate()

    def can_attempt(self):
        owner = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return False

        if (
            self._requires_shield_stack()
            and not self._shield_stack_options(owner)
        ):
            return False

        if self.selection == "choose":
            return bool(self._matching_cards(owner))

        if self.selection == "top":
            cards = self._visible_source_cards(owner)
            return bool(cards) and self._matches(cards[0])

        if self.selection == "bottom":
            cards = self._visible_source_cards(owner)
            return bool(cards) and self._matches(cards[-1])

        if self.selection == "first_matching":
            return bool(self._matching_cards(owner))

        if self.selection == "source_card":
            return self._source_card_candidate(owner) is not None

        raise ValueError(
            f"Unknown movement selection: {self.selection}"
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

        moved_cards = []
        limit = self._amount_limit()
        failed_cards = []
        while (
            limit is None
            or len(moved_cards) < limit
        ):
            card = self._select_next(
                owner,
                excluded=failed_cards,
            )
            if card is None:
                break

            self._before_move(card)
            shield_stack_on = self._shield_stack_on(owner)
            if (
                self._requires_shield_stack()
                and shield_stack_on is None
            ):
                failed_cards.append(card)
                continue

            moved = self.game.card_mover.move(
                card=card,
                owner=owner,
                from_zone=self.from_zone,
                to_zone=self.to_zone,
                reason=self.reason,
                evolution_mode=self.evolution_mode,
                shield_face_up=self._shield_face_up(owner),
                shield_stack_on=shield_stack_on,
            )
            if moved:
                moved_cards.append(card)
                self._after_move(
                    card,
                    owner,
                )
            else:
                failed_cards.append(card)
                if self.selection != "choose":
                    break

        if self.store_as:
            self.package_context[self.store_as] = (
                moved_cards[0]
                if len(moved_cards) == 1
                else moved_cards
            )

        return bool(moved_cards)

    def _select_next(
        self,
        owner,
        excluded,
    ):
        if self.selection == "choose":
            options = [
                card
                for card in self._matching_cards(owner)
                if card not in excluded
            ]
            if not options:
                return None

            return self.game.target_selector.select(
                self.player,
                options,
                prompt=self.prompt,
                can_skip=self.optional,
            )

        if self.selection == "top":
            cards = self._visible_source_cards(owner)
            if not cards:
                return None

            card = cards[0]
            if card in excluded:
                return None

            return (
                card
                if self._matches(card)
                else None
            )

        if self.selection == "bottom":
            cards = self._visible_source_cards(owner)
            if not cards:
                return None

            card = cards[-1]
            if card in excluded:
                return None

            return (
                card
                if self._matches(card)
                else None
            )

        if self.selection == "first_matching":
            for card in self._matching_cards(owner):
                if card not in excluded:
                    return card
            return None

        if self.selection == "source_card":
            card = self._source_card_candidate(owner)
            if card in excluded:
                return None

            return card

        raise ValueError(
            f"Unknown movement selection: {self.selection}"
        )

    def _matching_cards(
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
            for card in self._visible_source_cards(owner)
            if self._matches(card)
        ]

    def _source_card_candidate(
        self,
        owner,
    ):
        card = self.source_card
        if card is None:
            return None

        if not self._source_card_continuity_matches(card):
            return None

        if card not in self._visible_source_cards(owner):
            return None

        return (
            card
            if self._matches(card)
            else None
        )

    def _source_card_continuity_matches(
        self,
        card,
    ):
        if self.trigger_snapshot is None:
            return True

        expected_counter = self.trigger_snapshot.zone_change_counter
        if self.trigger_snapshot.zone != self.from_zone:
            expected_counter += 1

        return (
            getattr(
                card,
                "zone_change_counter",
                None,
            )
            == expected_counter
        )

    def _matches(
        self,
        card,
    ):
        return matches_card_filter_dsl_or_legacy(
            self.game,
            card,
            self.filter_spec,
            context=self._filter_context(),
            usage_type=self._usage_type(),
        )

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

        cards = owner.get_zone(
            self.from_zone
        ).cards
        return visible_cards(cards)

    def _filter_context(
        self,
    ):
        return {
            **self.package_context,
            "player": self.player,
        }

    def _usage_type(
        self,
    ):
        value = self.filter_spec.get(
            "type",
            self.filter_spec.get("card_type"),
        )
        return value if isinstance(value, str) else None

    def _amount_limit(
        self,
    ):
        if self.amount == "all":
            return None

        return int(
            resolve_effect_amount(
                game=self.game,
                player=self.player,
                amount=self.amount,
                min_amount=self.min_amount,
                max_amount=self.max_amount,
                prompt=f"Choose amount for: {self.prompt}",
            )
        )

    def _confirm(
        self,
        owner,
    ):
        if not self._matching_cards(owner):
            return False

        return self.game.choice_manager.select(
            self.player,
            [
                True,
                False,
            ],
            prompt=self.prompt,
        )

    def _shield_face_up(
        self,
        owner,
    ):
        if self.to_zone != ZoneType.SHIELD:
            return None

        face = self._choose_face(owner)
        return face == "face_up"

    def _shield_stack_on(
        self,
        owner,
    ):
        if not self._requires_shield_stack():
            return None

        options = self._shield_stack_options(owner)
        if not options:
            return None

        return self.game.target_selector.select(
            self.player,
            options,
            prompt="Choose shield slot to stack on",
        )

    def _shield_stack_options(
        self,
        owner,
    ):
        if self.to_zone != ZoneType.SHIELD:
            return []

        visible_shields = getattr(
            owner.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(owner.shield_zone.cards)

    def _requires_shield_stack(
        self,
    ):
        return (
            self.to_zone == ZoneType.SHIELD
            and self.shield_placement in (
                "choose_slot",
                "stack",
                "stack_on_slot",
            )
        )

    def _choose_face(
        self,
        owner,
    ):
        if len(self.face_options) == 1:
            return self.face_options[0]

        return self.game.choice_manager.select(
            owner,
            list(self.face_options),
            prompt="Choose shield face",
        )

    def _before_move(
        self,
        card,
    ):
        return None

    def _after_move(
        self,
        card,
        owner,
    ):
        if self.tapped is not None:
            card.tapped = bool(self.tapped)

        if self.destination_position == "top":
            destination = owner.get_zone(
                self.to_zone
            )
            if card in destination.cards:
                destination.cards.remove(card)
                destination.cards.insert(
                    0,
                    card,
                )

    def _validate(
        self,
    ):
        allowed_selections = (
            "bottom",
            "choose",
            "first_matching",
            "source_card",
            "top",
        )
        if self.selection not in allowed_selections:
            raise ValueError(
                f"Unknown movement selection: {self.selection}"
            )

        allowed_faces = (
            "face_down",
            "face_up",
        )
        for face in self.face_options:
            if face not in allowed_faces:
                raise ValueError(
                    f"Unknown shield face option: {face}"
                )

        if self.destination_position not in (
            None,
            "bottom",
            "top",
        ):
            raise ValueError(
                "destination_position must be top or bottom"
            )

        if self.shield_placement not in (
            "choose_slot",
            "new",
            "new_slot",
            "stack",
            "stack_on_slot",
        ):
            raise ValueError(
                f"Unknown shield placement: {self.shield_placement}"
            )
