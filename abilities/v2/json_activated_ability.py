"""Activated ability implementation for v2 JSON specs."""

from abilities.base.activated_ability import ActivatedAbility
from abilities.v2.spec_schema import ability_id
from abilities.v2.timing_matcher import ActivationTimingMatcher
from core.condition_evaluator import ConditionEvaluator
from core.target_resolver import TargetResolver
from effects.composition.packaged_effect import PackagedEffect
from effects.effect_context import EffectContext
from effects.effect_factory import EffectFactory


class JsonActivatedAbility(ActivatedAbility):
    COST_CHECK_HANDLERS = {
        "pay_mana": "_can_pay_mana_cost",
        "tap_self": "_can_tap_self_cost",
    }

    COST_PAYMENT_HANDLERS = {
        "pay_mana": "_pay_mana_cost",
        "tap_self": "_pay_tap_self_cost",
    }

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
        self.ability_id = ability_id(spec, "v2_activated")
        self.timing = spec.get("timing", {})
        self.condition_spec = spec.get(
            "condition",
            {
                "type": "always",
            },
        )
        self.active_if_spec = spec.get(
            "active_if",
            {
                "type": "always",
            },
        )
        self.costs = spec.get("costs", [])
        self.targets = spec.get("targets", [])
        self.effect_specs = spec.get("effects", [])
        self.label = spec.get("label", self.ability_id)
        self.timing_matcher = ActivationTimingMatcher(
            game,
            owner_card,
            self.timing,
        )
        self.active_zones = self.timing_matcher.active_zones()

    def can_activate(
        self,
        player,
    ):
        return (
            player == self.owner_card.owner
            and self.timing_matcher.matches()
            and self._condition_matches(player)
            and self._can_pay_costs(player)
        )

    def activate(
        self,
        action,
    ):
        if not self.can_activate(action.player):
            return False

        if not self._pay_costs(action.player):
            return False

        package_context = {}
        effect_context = EffectContext.from_package_context(
            package_context
        )
        target_resolution = TargetResolver(
            self.game
        ).resolve(
            self.targets,
            {
                "game": self.game,
                "player": action.player,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
                "package_context": package_context,
                "effect_context": effect_context,
            },
        )
        if not target_resolution.success:
            return False

        effects = EffectFactory(
            self.game
        ).build_many(
            self.effect_specs,
            action.player,
            source_card=self.owner_card,
        )
        package = PackagedEffect(
            effects,
            label=self.label,
        )
        package.package_context = package_context
        package.source_card = self.owner_card
        self.game.effect_resolver.add_effect(
            package,
            controller=action.player,
        )
        return True

    def _condition_matches(
        self,
        player,
    ):
        evaluator = ConditionEvaluator(
            self.game
        )
        context = {
            "game": self.game,
            "player": player,
            "controller": self.owner_card.owner,
            "source_card": self.owner_card,
        }
        return evaluator.evaluate(
            self.active_if_spec,
            context,
        ) and evaluator.evaluate(
            self.condition_spec,
            context,
        )

    def _can_pay_costs(
        self,
        player,
    ):
        for cost in self.costs:
            cost_type = cost.get("type")
            handler_name = self.COST_CHECK_HANDLERS.get(cost_type)
            if handler_name is None:
                raise ValueError(
                    f"Unknown activated ability cost: {cost_type}"
                )
            if not getattr(self, handler_name)(player, cost):
                return False

        return True

    def _pay_costs(
        self,
        player,
    ):
        for cost in self.costs:
            cost_type = cost.get("type")
            handler_name = self.COST_PAYMENT_HANDLERS.get(cost_type)
            if handler_name is None:
                raise ValueError(
                    f"Unknown activated ability cost: {cost_type}"
                )
            if not getattr(self, handler_name)(player, cost):
                return False

        return True

    def _can_pay_mana_cost(
        self,
        player,
        cost,
    ):
        return player.can_pay_cost(
            int(cost.get("amount", 0))
        )

    def _can_tap_self_cost(
        self,
        player,
        cost,
    ):
        return not getattr(
            self.owner_card,
            "tapped",
            False,
        )

    def _pay_mana_cost(
        self,
        player,
        cost,
    ):
        return player.tap_mana(
            int(cost.get("amount", 0)),
            choice_manager=(
                self.game.choice_manager
            ),
        )

    def _pay_tap_self_cost(
        self,
        player,
        cost,
    ):
        self.owner_card.tapped = True
        return True
