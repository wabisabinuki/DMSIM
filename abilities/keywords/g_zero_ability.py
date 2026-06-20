"""G-Zero keyword ability."""

from abilities.base.base_ability import BaseAbility
from core.condition_evaluator import ConditionEvaluator


class GZeroAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game=None,
        condition=None,
        label=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.condition = condition
        self.label = label or "G-Zero"

    def can_use(
        self,
        game,
        player,
        card,
    ):
        condition = self.condition
        if condition is None:
            return False

        if callable(condition):
            return bool(
                condition(
                    game,
                    player,
                    card,
                )
            )

        return ConditionEvaluator(game).evaluate(
            condition,
            {
                "game": game,
                "player": player,
                "controller": player,
                "source_card": card,
                "ability": self,
            },
        )


def build_g_zero_ability(
    spec,
    card,
    game,
):
    condition = spec.get("condition")
    min_creatures = spec.get(
        "min_creatures",
        spec.get(
            "creature_count",
            spec.get("count"),
        ),
    )

    if condition is None and min_creatures is not None:
        scope = spec.get("scope", "all")
        condition = _min_creatures_condition(
            int(min_creatures),
            scope,
        )

    return GZeroAbility(
        owner_card=card,
        game=game,
        condition=condition,
        label=spec.get("label"),
    )


def _min_creatures_condition(
    minimum,
    scope,
):
    def condition(
        game,
        player,
        card,
    ):
        if scope in (
            "controller",
            "owner",
            "self",
            "own",
            "own_creatures",
        ):
            creatures = game.query.get_creatures(
                controller=player
            )
        else:
            creatures = game.query.get_creatures()

        return len(creatures) >= minimum

    return condition
