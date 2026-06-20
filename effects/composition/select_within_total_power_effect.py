"""パワーの合計が上限以下になるよう、対象を任意で複数選びリストに収集する効果。"""

from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.ref_resolver import RefResolver
from effects.base.base_effect import BaseEffect
from effects.composition.card_predicates import _card_power


class SelectWithinTotalPowerEffect(BaseEffect):
    """選んだ対象のパワー合計が max_total_power を超えない範囲で、任意の数だけ選択する。

    まだ選んでいない対象のうち「今選ぶと合計が上限以下に収まる」ものだけを
    選択肢として提示し、プレイヤーがスキップするか選べる対象が尽きるまで繰り返す。
    選択結果は package_context[store_as] にリストとして格納される。

    「パワーの合計が N 以下になるように好きな数選ぶ」能力で使う。
    実際の効果（破壊など）は for_each_stored 等で別途適用する。
    """

    def __init__(
        self,
        player,
        game,
        candidates,
        filter_spec,
        store_as,
        max_total_power,
        optional=True,
        prompt=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.candidates = candidates
        self.filter_spec = filter_spec or {}
        self.store_as = store_as
        self.max_total_power = max_total_power
        self.optional = optional
        self.prompt = prompt or "Choose a target"

    def _resolved_max_total_power(self):
        # 数値はそのまま。"source_power" / {"ref": "source", "field": "power"} は
        # 発生源の現在パワー（マナ武装等の修整込み）を上限にする。
        value = self.max_total_power
        if value == "source_power" or (
            isinstance(value, dict)
            and value.get("ref") in ("source", "self")
            and value.get("field", "power") == "power"
        ):
            source_info = self.source_info
            if source_info is not None:
                return source_info.get_property("power") or 0

            if self.source_card is None:
                return 0
            return _card_power(self.source_card)

        if isinstance(value, dict):
            return RefResolver(
                self.game
            ).resolve(
                value,
                {
                    "player": self.player,
                    "controller": self.player,
                    "source_card": self.source_card,
                    "source_info": self.source_info,
                    "package_context": self.package_context,
                },
            )
        return value

    def resolve(self):
        selected = []
        selected_power = 0
        self._max_total_power_value = self._resolved_max_total_power()

        while True:
            options = self._valid_options(selected, selected_power)
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
            selected_power += _card_power(target)

        self.package_context[self.store_as] = selected
        return True

    def _valid_options(self, already_selected, selected_power):
        remaining = self._max_total_power_value - selected_power
        return [
            card
            for card in self._candidates()
            if card not in already_selected
            and _card_power(card) <= remaining
            and matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.filter_spec,
                context={
                    "player": self.player,
                    "source_card": self.source_card,
                    "source_info": self.source_info,
                },
            )
        ]

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

        raise ValueError(f"Unknown candidates: {self.candidates}")
