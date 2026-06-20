"""指定コストのカードを実行（プレイ）できなくする期間限定ロック。

「次の自分のターンのはじめまで、相手はそのコストのカードを実行できない」を表す汎用部品。
解決時に対象プレイヤー（既定は相手）へ自身を登録し、ActionValidator が各プレイ宣言時に
``prevents_execution`` を参照してコスト一致のプレイを弾く。期間は DurationEffectManager が
管理し、満了時に登録を外す。``cost`` には固定値のほか、同じパッケージ内で先に決めた数字の
stored 参照（`{"ref": "..."}` / `{"from": "stored", "key": "..."}`）も渡せる。
``card_filter`` を渡すと、コスト一致かつフィルタに合致するカードのみを弾く
（例: `{"card_type": "spell"}` で「そのコストの呪文だけ唱えられない」を表現する）。
"""

from effects.base.duration_effect import DurationEffect
from core.card_filter_evaluator import CardFilterEvaluator


class CostExecutionLockEffect(DurationEffect):

    def __init__(
        self,
        game,
        affected_player,
        cost,
        duration_type,
        source_card=None,
        card_filter=None,
    ):
        super().__init__(source_card, duration_type, game)
        self.affected_player = affected_player
        self.cost_spec = cost
        self.card_filter = card_filter
        self.locked_cost = None

    def can_resolve(self, game_state):
        return True

    def resolve(self):
        if self.affected_player is None:
            return False

        self.locked_cost = self._resolve_cost()
        if self.locked_cost is None:
            return False

        locks = getattr(self.affected_player, "execution_locks", None)
        if locks is None:
            locks = []
            self.affected_player.execution_locks = locks
        locks.append(self)

        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(self)
        return True

    def unapply(self):
        locks = getattr(self.affected_player, "execution_locks", [])
        if self in locks:
            locks.remove(self)
        super().unapply()

    def prevents_execution(self, card):
        if not self.is_active or self.locked_cost is None:
            return False
        if self._card_cost(card) != self.locked_cost:
            return False
        if self.card_filter and not CardFilterEvaluator(self.game).matches(
            card,
            self.card_filter,
        ):
            return False
        return True

    def _resolve_cost(self):
        cost = self.cost_spec
        if isinstance(cost, dict):
            key = cost.get("ref") or cost.get("key")
            return self.package_context.get(key) if key else None
        return cost

    def _card_cost(self, card):
        get_current_cost = getattr(card, "get_current_cost", None)
        if get_current_cost is not None:
            try:
                return get_current_cost()
            except (TypeError, ValueError):
                pass
        return getattr(card, "cost", None)
