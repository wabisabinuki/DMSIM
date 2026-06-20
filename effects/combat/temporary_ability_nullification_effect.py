"""クリーチャーの能力を一定期間無視する（能力無視）効果。"""

from core.creature_scope import creatures_for_scope
from effects.base.duration_effect import DurationEffect


class TemporaryAbilityNullificationEffect(DurationEffect):
    """対象クリーチャーの持つ能力（付与された能力を含む）を期間中無視する。

    能力そのものではない一時効果（攻撃制限など）は ``abilities`` ではなく
    別のリストで管理されるため、この無視の影響を受けない。
    """

    def __init__(
        self,
        game,
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
        self.targets = []

    def can_resolve(
        self,
        game_state,
    ):
        return True

    def resolve(
        self,
    ):
        if self.source_card is None and self.target_card is None:
            return

        self.targets = self._resolve_targets()

        for target in self.targets:
            nullifications = getattr(
                target,
                "temporary_ability_nullifications",
                None,
            )
            if nullifications is None:
                nullifications = []
                target.temporary_ability_nullifications = nullifications

            nullifications.append(self)

        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(
            self
        )

    def unapply(
        self,
    ):
        for target in self.targets:
            nullifications = getattr(
                target,
                "temporary_ability_nullifications",
                [],
            )
            if self in nullifications:
                nullifications.remove(self)

        super().unapply()

    def nullifies_abilities(
        self,
    ):
        return self.is_active

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
            "TemporaryAbilityNullificationEffect("
            f"scope={self.scope}, "
            f"until {self.duration_type})"
        )
