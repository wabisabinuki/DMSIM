"""自分（または指定プレイヤー）のクリーチャーの召喚コストを継続的に軽減する能力。

v2 静的能力の ``type: "cost_modifier"`` から生成される。召喚するカード自身では
なく、このパーマネント（例: シールドゾーンの G城）が他のクリーチャーの召喚
コストを修飾するため、`core/cost_modifiers.py` 経由で `modify_summon_cost` が
呼ばれる。

modifier の主なキー:
- ``amount``   : コストへの増減（``-1`` で 1 軽減）。
- ``min_cost`` : 軽減後の下限コスト（既定 1。「コストは0以下にならない」）。
- ``per_turn`` : 各ターンの適用回数上限（``1`` で「各ターンに1度」。省略で無制限）。
- ``optional`` : 「してもよい」。常に有利なため自動適用するが、軽減が無意味な
                 （下限に張り付く）場合は適用扱いにせず使用回数も消費しない。
"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.v2.spec_schema import ability_id
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.condition_evaluator import ConditionEvaluator


class SummonCostReductionAbility(ContinuousAbility):

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
        self.ability_id = ability_id(spec, "v2_cost_modifier")

        modifier = spec.get("modifier", {})
        self.amount = int(modifier.get("amount", -1))
        self.min_cost = int(modifier.get("min_cost", 1))
        self.optional = bool(modifier.get("optional", False))
        per_turn = modifier.get("per_turn")
        self.per_turn = None if per_turn is None else int(per_turn)

        applies_to = spec.get("applies_to", {})
        self.target_player = applies_to.get("player", "controller")
        self.filter_spec = applies_to.get(
            "filter",
            {
                key: value
                for key, value in applies_to.items()
                if key != "player"
            },
        )

        self.condition = spec.get(
            "condition",
            {
                "type": "always",
            },
        )

        # ターン番号 -> このターンに適用した回数
        self._uses_by_turn = {}

    def modify_summon_cost(
        self,
        summoned_card,
        player,
        cost,
        game,
        consume=False,
        interactive=False,
    ):
        if not self._applies(summoned_card, player, game):
            return cost

        turn = self._current_turn(game)
        if not self._available(turn):
            return cost

        reduced = max(
            self.min_cost,
            cost + self.amount,
        )
        if reduced == cost:
            # 下限に張り付くなど、軽減が無意味な場合は使用回数を消費しない。
            return cost

        # 「してもよい」効果は、実際の召喚時（interactive=True）に限り
        # プレイヤーへ使用可否を尋ねる。コスト計算・支払い可否判定など
        # 非対話の呼び出しでは、常に有利なため適用済みとして扱う。
        if (
            self.optional
            and interactive
            and not self._ask_player(
                summoned_card,
                player,
                game,
                cost - reduced,
            )
        ):
            return cost

        if consume and turn is not None:
            self._uses_by_turn[turn] = (
                self._uses_by_turn.get(turn, 0) + 1
            )

        return reduced

    def _ask_player(
        self,
        summoned_card,
        player,
        game,
        reduction,
    ):
        manager = getattr(game, "choice_manager", None)
        if manager is None:
            return True

        name = (
            getattr(summoned_card, "name_ja", None)
            or getattr(summoned_card, "name", "このクリーチャー")
        )
        apply_label = f"召喚コストを{reduction}少なくする"
        decline_label = "そのまま支払う"
        selected = manager.select(
            player,
            [apply_label, decline_label],
            prompt=(
                f"{name} の召喚コストを{reduction}"
                f"少なくしますか？"
            ),
            min_count=1,
            max_count=1,
        )
        return selected == apply_label

    def _applies(
        self,
        summoned_card,
        player,
        game,
    ):
        if self._resolve_target_player() is not player:
            return False

        if not self._matches_filter(summoned_card, player, game):
            return False

        return ConditionEvaluator(game).evaluate(
            self.condition,
            {
                "game": game,
                "player": getattr(self.owner_card, "owner", None),
                "controller": getattr(self.owner_card, "owner", None),
                "source_card": self.owner_card,
            },
        )

    def _matches_filter(self, summoned_card, player, game):
        # 召喚処理中、対象カードは pending 状態になっている。CardFilterEvaluator は
        # pending カードを一律に除外するため、フィルタ評価の間だけ pending を外して
        # 「これから召喚されるカードの種別」で判定する（直後に必ず元へ戻す）。
        was_pending = getattr(summoned_card, "is_pending", False)
        if was_pending:
            summoned_card.is_pending = False
        try:
            return matches_card_filter_dsl_or_legacy(
                game,
                summoned_card,
                self.filter_spec,
                context={
                    "game": game,
                    "player": player,
                    "controller": player,
                    "source_card": self.owner_card,
                },
            )
        finally:
            if was_pending:
                summoned_card.is_pending = True

    def _resolve_target_player(self):
        if self.target_player in (
            None,
            "controller",
            "self",
            "owner",
        ):
            return getattr(self.owner_card, "owner", None)

        return self.target_player

    def _available(self, turn):
        if self.per_turn is None:
            return True

        return self._uses_by_turn.get(turn, 0) < self.per_turn

    def _current_turn(self, game):
        state = getattr(game, "state", None)
        return getattr(state, "turn", None)
