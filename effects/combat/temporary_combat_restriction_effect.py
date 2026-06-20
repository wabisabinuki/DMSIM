"""Temporarily prevents creatures from attacking and/or blocking."""

from core.duration_type import DurationType
from core.creature_scope import creatures_for_scope
from effects.base.duration_effect import DurationEffect


class TemporaryCombatRestrictionEffect(DurationEffect):

    def __init__(
        self,
        game,
        restrictions,
        duration_type,
        source_card=None,
        scope="opponent_creatures",
        target_card=None,
    ):
        super().__init__(
            source_card,
            duration_type,
            game,
        )
        self.scope = scope
        self.target_card = target_card
        self.restrictions = tuple(restrictions)
        self.targets = []

    def can_resolve(
        self,
        game_state,
    ):

        return True

    def resolve(
        self,
    ):

        if self.source_card is None:
            return

        self.targets = self._resolve_targets()

        for target in self.targets:
            restrictions = getattr(
                target,
                "temporary_combat_restrictions",
                None,
            )
            if restrictions is None:
                restrictions = []
                target.temporary_combat_restrictions = restrictions

            restrictions.append(self)

        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(
            self
        )

        print(
            "[Effect] Applied temporary combat restrictions "
            f"{self.restrictions} to {len(self.targets)} creature(s) "
            f"until {self.duration_type}"
        )

    def unapply(
        self,
    ):

        for target in self.targets:
            restrictions = getattr(
                target,
                "temporary_combat_restrictions",
                [],
            )
            if self in restrictions:
                restrictions.remove(self)

        super().unapply()

    def prevents_attack(
        self,
    ):

        return self.is_active and "attack" in self.restrictions

    def prevents_block(
        self,
    ):

        return self.is_active and "block" in self.restrictions

    def prevents_attack_player(
        self,
    ):
        # "attack" は攻撃そのものを禁止するため、プレイヤー攻撃も含めて禁止になる。
        # "attack_player" はプレイヤーへの攻撃だけを禁止する（クリーチャー攻撃は可能）。
        return self.is_active and (
            "attack" in self.restrictions
            or "attack_player" in self.restrictions
        )

    def _resolve_targets(
        self,
    ):

        if self.target_card is not None:
            return [
                self.target_card,
            ]

        return creatures_for_scope(
            self.game,
            self.scope,
            self.source_card,
        )

    def __str__(
        self,
    ):

        return (
            "TemporaryCombatRestrictionEffect("
            f"{','.join(self.restrictions)}, "
            f"scope={self.scope}, "
            f"until {self.duration_type})"
        )
