"""自身の召喚コストを継続的に増減する能力。

v2 静的能力 ``type: "cost_modifier"`` のうち ``applies_to.card == "self"`` の
形から生成される。他カードを軽減する `SummonCostReductionAbility` と異なり、
このカード自身の `Card.get_current_cost` から `modify_cost` 経由で呼ばれる。

主なキー:
- ``applies_to.from_zone`` : このゾーンから召喚する場合のみ適用
                             （例: ``"hand"`` で「手札から召喚するなら」）。
- ``modifier.amount``      : コストへの増減（``3`` で 3 多くする）。
- ``modifier.min_cost``    : 修正後の下限コスト（既定 1）。
- ``modifier.per_count``   : 条件に合うカード1枚につき amount を適用する。

注意: ``condition`` または ``per_count`` を使う場合、修正値の算出に盤面参照が
必要なため、``Card.get_current_cost`` の呼び出し元が ``game`` を渡していないと
軽減は適用されない（安全側に倒して素のコストを返す）。表示用にコストを
取得する経路でも ``game`` を渡すこと。
"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.v2.spec_schema import ability_id
from core.card_filter_evaluator import CardFilterEvaluator
from core.condition_evaluator import ConditionEvaluator
from core.pending_cards import visible_cards
from core.ref_resolver import RefResolver
from effects.zones.zone_effect_utils import parse_zone


class SelfSummonCostModifierAbility(ContinuousAbility):

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
        self.ability_id = ability_id(spec, "v2_self_cost_modifier")

        modifier = spec.get("modifier", {})
        self.amount = int(modifier.get("amount", 0))
        self.min_cost = int(modifier.get("min_cost", 1))
        self.per_count = modifier.get("per_count")
        self.condition = spec.get(
            "condition",
            {
                "type": "always",
            },
        )

        applies_to = spec.get("applies_to", {})
        from_zone = applies_to.get("from_zone")
        self.from_zone = (
            None
            if from_zone is None
            else parse_zone(from_zone)
        )

    def modify_cost(
        self,
        card,
        player,
        cost,
        game=None,
    ):
        if card is not self.owner_card:
            return cost

        if (
            self.from_zone is not None
            and getattr(card, "zone", None) != self.from_zone
        ):
            return cost

        if game is None and self.condition.get("type") != "always":
            return cost

        if game is not None and not self._condition_matches(
            player,
            game,
        ):
            return cost

        amount = self._effective_amount(
            player,
            game,
        )
        return max(
            self.min_cost,
            cost + amount,
        )

    def _condition_matches(
        self,
        player,
        game,
    ):
        return ConditionEvaluator(game).evaluate(
            self.condition,
            {
                "game": game,
                "player": player or self.owner_card.owner,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
            },
        )

    def _effective_amount(
        self,
        player,
        game,
    ):
        if not self.per_count:
            return self.amount

        if game is None:
            return 0

        return self.amount * self._matching_count(
            player,
            game,
        )

    def _matching_count(
        self,
        player,
        game,
    ):
        cards = self._count_cards(
            self.per_count,
            player,
            game,
        )
        filter_spec = self.per_count.get("filter", {})
        if not filter_spec:
            return len(cards)

        evaluator = CardFilterEvaluator(game)
        context = {
            "game": game,
            "player": player or self.owner_card.owner,
            "controller": self.owner_card.owner,
            "source_card": self.owner_card,
        }
        return sum(
            1
            for card in cards
            if evaluator.matches(
                card,
                filter_spec,
                context,
            )
        )

    def _count_cards(
        self,
        count_spec,
        player,
        game,
    ):
        source = count_spec.get(
            "from",
            {
                "player": "controller",
                "zone": "battle",
            },
        )
        if isinstance(source, dict):
            owner = self._resolve_player(
                source.get("player", "controller"),
                player,
                game,
            )
            if owner is None:
                return []
            zone = parse_zone(source.get("zone", "battle"))
            return visible_cards(
                owner.get_zone(zone).cards
            )

        context = {
            "game": game,
            "player": player or self.owner_card.owner,
            "controller": self.owner_card.owner,
            "source_card": self.owner_card,
        }
        resolved = RefResolver(game).resolve(
            source,
            context,
        )
        if hasattr(resolved, "cards"):
            return visible_cards(resolved.cards)
        if isinstance(resolved, list):
            return [
                card
                for card in resolved
                if card is not None
            ]
        return []

    def _resolve_player(
        self,
        value,
        player,
        game,
    ):
        if value in (
            None,
            "controller",
            "self",
            "owner",
        ):
            return self.owner_card.owner
        if value == "current":
            return player
        if value == "opponent":
            return game.query.get_opponent(
                self.owner_card.owner
            )
        return value
