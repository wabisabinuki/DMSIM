"""ソウルシフト：このクリーチャーの召喚コストを進化元のコストの数だけ少なくする。

進化クリーチャー専用の召喚コスト軽減。軽減量は「進化元に選んだクリーチャーの
コスト」に等しい（``source_count`` が複数なら合計）。コストは 0 以下にならない
（下限 1）。

軽減量は進化元の選択結果に依存するため、``modify_cost`` は次の順で参照する:

1. 実際の召喚処理中（``SummonActionHandler``）にプレイヤーが選んだ進化元が
   ``card._soulshift_source`` に入っていれば、それのコスト合計で軽減する。
2. まだ進化元が確定していない（アクション生成・合法性判定・表示）段階では、
   現在の進化元候補から最大の軽減になる組み合わせ（コストの高い順に
   ``source_count`` 体）を仮定して軽減する。これにより「軽減後なら払える」
   召喚を合法手として提示できる。実際の支払いは進化元確定後に再計算される。
"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.keywords.evolution_ability import EvolutionAbility


class SoulshiftAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        min_cost=1,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.min_cost = min_cost

    def modify_cost(
        self,
        card,
        player,
        cost,
        game=None,
    ):
        if card is not self.owner_card:
            return cost

        sources = self._reduction_sources(
            card,
            player,
        )
        reduction = sum(
            getattr(source, "cost", 0) or 0
            for source in sources
        )
        if reduction <= 0:
            return cost

        return max(
            self.min_cost,
            cost - reduction,
        )

    def _reduction_sources(
        self,
        card,
        player,
    ):
        pending = getattr(
            card,
            "_soulshift_source",
            None,
        )
        if pending is not None:
            return pending if isinstance(pending, list) else [pending]

        return self._best_case_sources(
            card,
            player,
        )

    def _best_case_sources(
        self,
        card,
        player,
    ):
        if player is None:
            player = getattr(
                self.owner_card,
                "owner",
                None,
            )
        if player is None:
            return []

        ability = self._evolution_ability(card)
        if ability is None:
            return []

        candidates = ability.source_candidates(
            player,
            card,
        )
        if not candidates:
            return []

        count = getattr(
            ability,
            "source_count",
            1,
        )
        return sorted(
            candidates,
            key=lambda candidate: getattr(candidate, "cost", 0) or 0,
            reverse=True,
        )[:count]

    def _evolution_ability(
        self,
        card,
    ):
        for ability in getattr(
            card,
            "abilities",
            [],
        ):
            if isinstance(
                ability,
                EvolutionAbility,
            ):
                return ability

        return None
