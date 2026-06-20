"""Structured static ability holder for v2 JSON abilities."""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.v2.spec_schema import ability_id
from core.condition_evaluator import ConditionEvaluator
from core.seal_utils import is_ignored_by_seal, is_seal_card


class StaticAbility(ContinuousAbility):
    """Store static rule/modifier specs that are not wired to engine hooks yet."""

    def __init__(
        self,
        owner_card,
        game,
        spec,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.spec = dict(spec)
        self.ability_id = ability_id(spec, "v2_static")
        self.static_type = spec.get("type")
        self.applies_to = spec.get("applies_to", {})
        self.condition = spec.get(
            "condition",
            {
                "type": "always",
            },
        )
        self.modifier = spec.get("modifier", {})
        self.rule = spec.get("rule", {})

    def is_active(
        self,
        player=None,
        event=None,
    ):
        if is_seal_card(self.owner_card) or is_ignored_by_seal(self.owner_card):
            return False

        return ConditionEvaluator(
            self.game
        ).evaluate(
            self.condition,
            {
                "game": self.game,
                "player": player
                or getattr(
                    self.owner_card,
                    "owner",
                    None,
                ),
                "source_card": self.owner_card,
                "event": event,
            },
        )
