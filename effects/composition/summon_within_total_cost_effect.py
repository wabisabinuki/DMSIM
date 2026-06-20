"""コスト合計の上限内で、複数ゾーンからクリーチャーを踏み倒す効果。

「コストの合計が N 以下になるように、クリーチャーを M 体まで自分の手札またはマナゾーンから
出す」を表す汎用部品。候補を1体ずつ選ばせ、選ぶたびに「残り選択数 < M」かつ
「選択済みコスト合計 + その候補のコスト <= N」を満たすものだけを提示する。0体で打ち切れる。
"""

from core.card_filter_evaluator import CardFilterEvaluator
from effects.base.base_effect import BaseEffect
from effects.composition.card_predicates import creature_cost
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class SummonWithinTotalCostEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
        from_zones,
        filter_spec,
        max_count,
        max_total_cost,
        summoning_sick=True,
        prompt=None,
        source_card=None,
        store_as=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.from_zones = from_zones or ["hand"]
        self.filter_spec = filter_spec or {"card_type": "creature"}
        self.max_count = max_count
        self.max_total_cost = max_total_cost
        self.summoning_sick = summoning_sick
        self.prompt = prompt
        self.source_card = source_card
        self.store_as = store_as

    def resolve(self):
        zone_of = self._candidate_zones()
        if not zone_of:
            if self.store_as:
                self.package_context[self.store_as] = []
            return False

        chosen = []
        total = 0
        while len(chosen) < self.max_count:
            selectable = [
                card
                for card in zone_of
                if card not in chosen
                and total + creature_cost(card) <= self.max_total_cost
            ]
            if not selectable:
                break

            pick = self.game.target_selector.select(
                self.player,
                selectable,
                prompt=self.prompt or "出すクリーチャーを選ぶ（コスト合計上限内）",
                can_skip=True,
            )
            if pick is None:
                break

            chosen.append(pick)
            total += creature_cost(pick)

        summoned_cards = []
        for card in chosen:
            if self._summon(card, zone_of[card]):
                summoned_cards.append(card)

        if self.store_as:
            self.package_context[self.store_as] = summoned_cards

        return bool(summoned_cards)

    def _candidate_zones(self):
        evaluator = CardFilterEvaluator(self.game)
        context = {
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
        }
        zone_of = {}
        for zone_name in self.from_zones:
            zone = parse_zone(zone_name)
            for card in list(self.player.get_zone(zone).cards):
                if evaluator.matches(card, self.filter_spec, context):
                    zone_of[card] = zone
        return zone_of

    def _summon(self, card, from_zone):
        moved = self.game.card_mover.move(
            card=card,
            owner=self.player,
            from_zone=from_zone,
            to_zone=ZoneType.BATTLE,
            reason="summon_within_total_cost",
        )
        if moved:
            card.summoning_sick = bool(self.summoning_sick)
        return moved
