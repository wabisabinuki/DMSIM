"""Timed power multiplier effect.

Multiplies a creature's power by a factor for the duration of the current turn.

``target_card`` を直接渡せば従来通りそのカードへ適用する。``target_spec`` を渡した
場合は解決時に package_context から対象を解決する（`{"ref": "..."}` などの stored 参照を
渡せる）ので、「選んだクリーチャー1体のパワーを2倍にする」といった効果に使える。
"""

from effects.base.duration_effect import DurationEffect
from core.duration_type import DurationType
from core.effect_argument_resolver import EffectArgumentResolver
from core.protocols import HasGameState
from modifiers.power_modifier import PowerModifier


class TimedPowerMultiplierEffect(DurationEffect):

    def __init__(
        self,
        source_card,
        target_card,
        factor: int,
        game: HasGameState,
        target_spec=None,
        player=None,
    ):
        super().__init__(
            source_card,
            DurationType.UNTIL_END_OF_TURN,
            game,
        )
        self.target_card = target_card
        self.target_spec = target_spec
        self.player = player
        self.factor = factor
        self.applied_modifiers = []

    def _targets(self):
        if self.target_spec is not None:
            resolver = EffectArgumentResolver(self.game)
            context = resolver.context(
                self.player,
                source_card=self.source_card,
                package_context=self.package_context,
            )
            return resolver.cards(self.target_spec, context)

        if self.target_card is None:
            return []

        return [self.target_card]

    def resolve(self):
        targets = self._targets()
        if not targets:
            return

        for target in targets:
            if self.trigger_snapshot is not None and target is self.target_card:
                if not self.trigger_snapshot.is_still_in_battle(target):
                    continue

            modifier = PowerModifier(kind="multiply", factor=self.factor)
            modifier.source_effect = self
            target.power_modifiers.append(modifier)
            self.applied_modifiers.append((target, modifier))

            print(
                f"[Effect] Applied x{self.factor} power multiplier to "
                f"{target} until end of turn"
            )

        self.register_duration()
        self.is_active = True

    def unapply(self):
        for target, modifier in self.applied_modifiers:
            if modifier in target.power_modifiers:
                target.power_modifiers.remove(modifier)
                print(
                    f"[Effect] Removed x{self.factor} multiplier from {target}"
                )
        self.applied_modifiers = []
        super().unapply()

    def __str__(self):
        return f"TimedPowerMultiplierEffect(x{self.factor})"
