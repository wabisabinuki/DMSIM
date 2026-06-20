"""Untap a target card."""

from effects.base.base_effect import BaseEffect
from effects.combat.target_reference import resolve_target_reference
from events.card_state_event import CardUntappedEvent


class UntapEffect(BaseEffect):

    def __init__(
        self,
        target,
        game=None,
        player=None,
    ):
        super().__init__()
        self.target = target
        self.game = game
        self.player = player

    def can_attempt(
        self,
    ):
        target = self._target()
        return target is not None and target.tapped

    def resolve(
        self,
    ):
        target = self._target()
        if target is None:
            return False

        was_tapped = target.tapped
        if not target.untap(
            player=self.player,
        ):
            return False

        if was_tapped and self.game is not None:
            self.game.event_manager.publish(
                CardUntappedEvent(
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
