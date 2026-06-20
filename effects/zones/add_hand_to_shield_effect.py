"""Effect that puts a hand card into the shield zone."""

from effects.base.base_effect import BaseEffect
from core.pending_cards import visible_cards
from zones.zone_type import ZoneType


class AddHandToShieldEffect(BaseEffect):

    DEFAULT_FACE_OPTIONS = (
        "face_up",
        "face_down",
    )

    def __init__(
        self,
        player,
        game,
        optional=True,
        face_options=None,
        shield_placement="new",
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.optional = optional
        self.face_options = tuple(
            face_options or self.DEFAULT_FACE_OPTIONS
        )
        self.shield_placement = shield_placement or "new"
        self._validate_face_options()
        self._validate_shield_placement()

    def can_attempt(self):
        if (
            self._requires_shield_stack()
            and not self._shield_stack_options()
        ):
            return False

        return bool(
            visible_cards(
                self.player.hand.cards
            )
        )

    def resolve(self):
        hand_cards = visible_cards(
            self.player.hand.cards
        )
        if not hand_cards:
            return False

        card = self.game.target_selector.select(
            self.player,
            hand_cards,
            prompt="Choose a hand card to shield",
            can_skip=self.optional,
        )
        if card is None:
            return False

        face = self._choose_face()
        shield_stack_on = self._shield_stack_on()
        if (
            self._requires_shield_stack()
            and shield_stack_on is None
        ):
            return False

        return self.game.card_mover.move(
            card=card,
            owner=self.player,
            from_zone=ZoneType.HAND,
            to_zone=ZoneType.SHIELD,
            reason="add_hand_to_shield",
            shield_face_up=(face == "face_up"),
            shield_stack_on=shield_stack_on,
        )

    def _choose_face(self):
        if len(self.face_options) == 1:
            return self.face_options[0]

        return self.game.choice_manager.select(
            self.player,
            list(self.face_options),
            prompt="Choose shield face",
        )

    def _validate_face_options(self):
        unknown = [
            face
            for face in self.face_options
            if face not in self.DEFAULT_FACE_OPTIONS
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

        options = self._shield_stack_options()
        if not options:
            return None

        return self.game.target_selector.select(
            self.player,
            options,
            prompt="Choose shield slot to stack on",
        )

    def _shield_stack_options(self):
        visible_shields = getattr(
            self.player.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(self.player.shield_zone.cards)

    def _requires_shield_stack(self):
        return self.shield_placement in (
            "choose_slot",
            "stack",
            "stack_on_slot",
        )

    def _validate_shield_placement(self):
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
