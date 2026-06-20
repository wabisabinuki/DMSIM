"""Release Hyper Mode for scoped creatures until next controller turn."""

from cards.card import SpecialType
from core.creature_scope import creatures_for_scope
from effects.base.base_effect import BaseEffect


class ReleaseHyperModeEffect(BaseEffect):
    """Unlock Hyper Mode on current scoped Hyper Mode creatures."""

    def __init__(
        self,
        game,
        scope,
        controller,
    ):
        super().__init__()
        self.game = game
        self.scope = scope
        self.controller = controller

    def can_attempt(
        self,
    ):
        return bool(self._targets())

    def resolve(
        self,
    ):
        targets = self._targets()
        if not targets:
            return False

        for target in targets:
            target.unlock_hyper_mode_until_next_turn_start(
                self.controller,
                self.game.state,
            )

        return True

    def _targets(
        self,
    ):
        if self.source_card is None:
            return []

        return [
            creature
            for creature in creatures_for_scope(
                self.game,
                self.scope,
                self.source_card,
            )
            if creature.has_special_type(SpecialType.HYPER_MODE)
        ]
