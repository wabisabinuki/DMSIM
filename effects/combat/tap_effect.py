"""Tap a target card."""

from effects.base.base_effect import BaseEffect
from effects.combat.target_reference import resolve_target_reference
from events.card_state_event import CardTappedEvent


class TapEffect(BaseEffect):

    def __init__(
        self,
        target,
        game=None,
        optional=False,
        prompt="tap this creature?",
    ):
        super().__init__()
        self.target = target
        self.game = game
        self.optional = optional
        self.prompt = prompt

    def can_attempt(
        self,
    ):
        return self._target() is not None

    def resolve(
        self,
    ):
        target = self._target()
        if target is None:
            return False

        if self.optional and self.game is not None:
            confirmed = self.game.target_selector.select(
                target.owner,
                [True],
                prompt=self.prompt,
                can_skip=True,
            )
            if confirmed is None:
                return False

        if target.tapped:
            return True

        target.tapped = True
        if self.game is not None:
            self.game.event_manager.publish(
                CardTappedEvent(
                    target.owner,
                    target,
                    reason="effect",
                )
            )
        return True

    def _target(
        self,
    ):
        return resolve_target_reference(
            self.target,
            self.package_context,
        )
