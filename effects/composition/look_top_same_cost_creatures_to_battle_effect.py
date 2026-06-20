"""山札上のカードがすべて同コストのクリーチャーならバトルゾーンに出す効果。"""

from effects.base.base_effect import BaseEffect
from effects.composition.card_predicates import (
    creature_cost,
    is_creature_card,
)
from zones.zone_type import ZoneType


class LookTopSameCostCreaturesToBattleEffect(BaseEffect):
    """上から N 枚を確認し、全て同コストクリーチャーなら全て出す。"""

    def __init__(
        self,
        game,
        player,
        amount,
        source_card=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.amount = amount
        self.source_card = source_card

    def resolve(self):
        seen = list(self.player.deck.cards[: self.amount])
        if not seen:
            return False

        if self._all_same_cost_creatures(seen):
            moved = False
            for card in list(seen):
                if self.game.card_mover.move(
                    card=card,
                    owner=self.player,
                    from_zone=ZoneType.DECK,
                    to_zone=ZoneType.BATTLE,
                    reason="look_top_same_cost_creatures_to_battle",
                ):
                    card.summoning_sick = True
                    moved = True
            return moved

        for card in self._choose_bottom_order(seen):
            if card in self.player.deck.cards:
                self.player.deck.remove(card)
                self.player.deck.add(card)
        return True

    def _all_same_cost_creatures(self, cards):
        if not all(is_creature_card(card) for card in cards):
            return False

        costs = {creature_cost(card) for card in cards}
        return len(costs) == 1

    def _choose_bottom_order(self, cards):
        if len(cards) <= 1:
            return cards

        selected = self.game.target_selector.select_multiple(
            self.player,
            cards,
            prompt="Choose order to put on bottom of deck",
            min_count=len(cards),
            max_count=len(cards),
        )
        return selected if len(selected) == len(cards) else cards
