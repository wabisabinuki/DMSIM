"""Apply Just Diver-style protection to a creature scope temporarily."""

from core.creature_scope import creatures_for_scope
from effects.base.base_effect import BaseEffect
from effects.combat.temporary_just_diver_effect import (
    TemporaryJustDiverEffect,
)


class ScopedTemporaryJustDiverEffect(BaseEffect):
    """Grant attack/block protection to current creatures in a scope."""

    def __init__(
        self,
        game,
        scope,
        duration_type,
    ):
        super().__init__()
        self.game = game
        self.scope = scope
        self.duration_type = duration_type

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
            TemporaryJustDiverEffect(
                game=self.game,
                target_card=target,
                duration_type=self.duration_type,
            ).resolve()

        return True

    def _targets(
        self,
    ):
        if self.source_card is None:
            return []

        return creatures_for_scope(
            self.game,
            self.scope,
            self.source_card,
        )
