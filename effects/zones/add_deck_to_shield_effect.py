"""Effect that puts cards from the top of a deck into shields."""

from effects.base.base_effect import BaseEffect
from core.ref_resolver import RefResolver
from effects.effect_context import EffectContext
from core.pending_cards import first_visible_card
from zones.zone_type import ZoneType


class AddDeckToShieldEffect(BaseEffect):

    DEFAULT_FACE_OPTIONS = (
        "face_down",
    )

    def __init__(
        self,
        player,
        game,
        amount=1,
        optional=False,
        face_options=None,
        shield_placement="new",
        shield_stack_on=None,
        store_as=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.amount = amount
        self.optional = optional
        self.shield_stack_on = shield_stack_on
        self.refs = RefResolver(game)
        self.face_options = tuple(
            face_options or self.DEFAULT_FACE_OPTIONS
        )
        self.shield_placement = shield_placement or "new"
        self.store_as = store_as
        self._validate_face_options()
        self._validate_shield_placement()

    def can_attempt(self):
        if (
            self._requires_shield_stack()
            and not self._shield_stack_options()
        ):
            return False

        return bool(
            first_visible_card(
                self.player.deck.cards
            )
        )

    def resolve(self):
        if first_visible_card(
            self.player.deck.cards
        ) is None:
            return False

        if self.optional:
            proceed = self.game.choice_manager.select(
                self.player,
                [True, False],
                prompt="Shield cards from deck?",
            )
            if not proceed:
                return False

        moved_cards = []
        for _ in range(self.amount):
            card = first_visible_card(
                self.player.deck.cards
            )
            if card is None:
                break

            face = self._choose_face()
            shield_stack_on = self._shield_stack_on()
            if (
                self._requires_shield_stack()
                and shield_stack_on is None
            ):
                break

            moved = self.game.card_mover.move(
                card=card,
                owner=self.player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.SHIELD,
                reason="add_deck_to_shield",
                shield_face_up=(face == "face_up"),
                shield_stack_on=shield_stack_on,
            )
            if moved:
                moved_cards.append(card)

        if self.store_as:
            self.package_context[self.store_as] = (
                moved_cards[0]
                if len(moved_cards) == 1
                else moved_cards
            )

        return bool(moved_cards)

    def _choose_face(self):
        if len(self.face_options) == 1:
            return self.face_options[0]

        return self.game.choice_manager.select(
            self.player,
            list(self.face_options),
            prompt="Choose shield face",
        )

    def _validate_face_options(self):
        allowed = (
            "face_up",
            "face_down",
        )
        unknown = [
            face
            for face in self.face_options
            if face not in allowed
        ]
        if unknown:
            raise ValueError(
                f"Unknown shield face option: {unknown[0]}"
            )

        if not self.face_options:
            raise ValueError("face_options cannot be empty")

    def _shield_stack_on(self):
        if not self._requires_shield_stack():
            return None

        explicit = self._explicit_shield_stack_on()
        if explicit is not None:
            return explicit

        options = self._shield_stack_options()
        if not options:
            return None

        return self.game.target_selector.select(
            self.player,
            options,
            prompt="Choose shield slot to stack on",
        )

    def _shield_stack_options(self):
        explicit = self._explicit_shield_stack_on()
        if explicit is not None:
            if explicit in self.player.shield_zone.cards:
                return [
                    explicit,
                ]
            return []

        visible_shields = getattr(
            self.player.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(self.player.shield_zone.cards)

    def _requires_shield_stack(self):
        return (
            self.shield_stack_on is not None
            or self.shield_placement in (
                "choose_slot",
                "specified_slot",
                "stack",
                "stack_on_slot",
            )
        )

    def _explicit_shield_stack_on(self):
        if self.shield_stack_on is None:
            return None

        return self.refs.resolve(
            self.shield_stack_on,
            self._context(),
        )

    def _context(self):
        package_context = getattr(
            self,
            "package_context",
            {},
        )
        return {
            "game": self.game,
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
            "package_context": package_context,
            "effect_context": EffectContext.from_package_context(
                package_context
            ),
        }

    def _validate_shield_placement(self):
        if self.shield_placement not in (
            "choose_slot",
            "new",
            "new_slot",
            "specified_slot",
            "stack",
            "stack_on_slot",
        ):
            raise ValueError(
                f"Unknown shield placement: {self.shield_placement}"
            )
