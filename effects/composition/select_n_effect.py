"""Select up to N optional targets, storing them as a list."""

from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.amount_choice import resolve_effect_amount
from effects.base.base_effect import BaseEffect


class SelectNEffect(BaseEffect):
    """count_key から取得した上限回数まで、対象を任意で選択しリストに収集する。

    プレイヤーがスキップした時点、または選べる対象がなくなった時点で停止する。
    すでに選んだカードは次の選択肢から除外される。
    選択結果は package_context[store_as] にリストとして格納される。

    「S・トリガー1枚につき相手クリーチャーを1体選ぶ」のように、
    選択ループと効果適用ループを分離すべき能力で使う。
    """

    def __init__(
        self,
        player,
        game,
        count_key,
        candidates,
        filter_spec,
        store_as,
        optional=True,
        prompt=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.count_key = count_key
        self.candidates = candidates
        self.filter_spec = filter_spec or {}
        self.store_as = store_as
        self.optional = optional
        self.prompt = prompt or "Choose a target"

    def resolve(self):
        count = self.package_context.get(self.count_key, 0)
        if not isinstance(count, int):
            count = 0

        maximum = min(count, len(self._valid_options([])))
        if maximum <= 0:
            self.package_context[self.store_as] = []
            return True

        # 「何体に適用するか（してもよい）」の判断は効果の持ち主が行う。
        # 個々の対象を「誰が選ぶか」は target_selector の置換に委ねるため、
        # ここでは self.player に直接 amount を尋ねる。
        if self.optional:
            amount = resolve_effect_amount(
                game=self.game,
                player=self.player,
                min_amount=0,
                max_amount=maximum,
                prompt=f"Choose how many for: {self.prompt}",
            )
        else:
            amount = maximum

        selected = []
        for _ in range(amount):
            options = self._valid_options(selected)
            if not options:
                break

            target = self.game.target_selector.select(
                self.player,
                options,
                prompt=self.prompt,
                can_skip=False,
            )
            if target is None:
                break
            selected.append(target)

        self.package_context[self.store_as] = selected
        return True

    def _valid_options(self, already_selected):
        return [
            card
            for card in self._candidates()
            if card not in already_selected
            and matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.filter_spec,
                context={
                    "player": self.player,
                    "source_card": self.source_card,
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
