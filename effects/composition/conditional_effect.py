"""
PackageContextの値を条件に、サブ効果を解決する効果。
"""

from effects.base.base_effect import BaseEffect
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy


class ConditionalEffect(BaseEffect):

    def __init__(
        self,
        key,
        condition,
        effects,
    ):
        super().__init__()

        self.key = key
        self.condition = condition
        self.effects = effects

    def resolve(self):
        value = self.package_context.get(
            self.key
        )

        if not matches_card_filter_dsl_or_legacy(
            None,
            value,
            self.condition,
            context=self.package_context,
        ):
            return

        for effect in self.effects:
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.trigger_snapshot = self.trigger_snapshot
            effect.condition_context = self.condition_context
            effect.package_context = self.package_context
            effect.resolve()
