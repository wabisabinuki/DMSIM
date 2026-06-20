"""コストの合計が上限以下になるよう、任意で複数対象を選ぶ効果。"""

from core.card_filter_evaluator import (
    CardFilterEvaluator,
    matches_card_filter_dsl_or_legacy,
)
from effects.base.base_effect import BaseEffect


class SelectWithinTotalCostEffect(BaseEffect):
    """選んだ対象のコスト合計が max_total_cost を超えない範囲で収集する。"""

    def __init__(
        self,
        player,
        game,
        candidates,
        filter_spec,
        store_as,
        max_total_cost,
        optional=True,
        prompt=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.candidates = candidates
        self.filter_spec = filter_spec or {}
        self.store_as = store_as
        self.max_total_cost = max_total_cost
        self.optional = optional
        self.prompt = prompt or "Choose a target"

    def resolve(self):
        selected = []
        selected_cost = 0

        while True:
            options = self._valid_options(selected, selected_cost)
            if not options:
                break

            target = self.game.target_selector.select(
                self.player,
                options,
                prompt=self.prompt,
                can_skip=self.optional,
            )
            if target is None:
                break

            selected.append(target)
            selected_cost += self._card_cost(target)

        self.package_context[self.store_as] = selected
        return True

    def _valid_options(self, already_selected, selected_cost):
        remaining = self.max_total_cost - selected_cost
        return [
            card
            for card in self._candidates()
            if card not in already_selected
            and self._card_cost(card) <= remaining
            and matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.filter_spec,
                context={
                    "player": self.player,
                    "controller": self.player,
                    "source_card": self.source_card,
                },
            )
        ]

    def _card_cost(self, card):
        context = {
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
        }
        return CardFilterEvaluator(self.game)._field_cost(card, context)

    def _candidates(self):
        if self.candidates == "opponent_creatures":
            opponent = self.game.query.get_opponent(self.player)
            return self.game.query.get_selectable_creatures(
                source=self.source_card or self.player,
                controller=opponent,
            )

        if self.candidates == "own_creatures":
            return self.game.query.get_selectable_creatures(
                source=self.source_card or self.player,
                controller=self.player,
            )

        if self.candidates == "creatures":
            return self.game.query.get_selectable_creatures(
                source=self.source_card or self.player,
            )

        if self.candidates == "opponent_battle_zone":
            return self.game.query.get_battle_cards(
                controller=self.game.query.get_opponent(self.player),
            )

        if self.candidates == "own_battle_zone":
            return self.game.query.get_battle_cards(
                controller=self.player,
            )

        raise ValueError(f"Unknown candidates: {self.candidates}")
