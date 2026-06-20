"""山札上から見たカードのうち、異なるカードタイプのカードを手札に加える効果。"""

from core.card_filter_evaluator import CardFilterEvaluator
from core.pending_cards import visible_cards
from effects.base.base_effect import BaseEffect
from zones.zone_type import ZoneType


class LookTopChooseDistinctTypesToHandEffect(BaseEffect):
    """上から N 枚を見て、カードタイプが重ならない範囲で好きな数を手札へ。"""

    def __init__(
        self,
        player,
        amount,
        game,
        optional=True,
        prompt=None,
    ):
        super().__init__()
        self.player = player
        self.amount = amount
        self.game = game
        self.optional = optional
        self.prompt = prompt or "手札に加えるカードを選ぶ"

    def resolve(self):
        seen = visible_cards(self.player.deck.cards)[: self.amount]
        if not seen:
            return False

        selected = []
        used_types = set()
        while True:
            candidates = [
                card
                for card in seen
                if card not in selected
                and self._card_types(card)
                and used_types.isdisjoint(self._card_types(card))
            ]
            if not candidates:
                break

            card = self.game.target_selector.select(
                self.player,
                candidates,
                prompt=self.prompt,
                can_skip=self.optional,
            )
            if card is None:
                break

            selected.append(card)
            used_types.update(self._card_types(card))

        moved_any = False
        for card in selected:
            moved_any = (
                self.game.card_mover.move(
                    card=card,
                    owner=self.player,
                    from_zone=ZoneType.DECK,
                    to_zone=ZoneType.HAND,
                    reason="look_top_choose_distinct_types_to_hand",
                )
                or moved_any
            )

        remaining = [
            card
            for card in seen
            if card not in selected and card in self.player.deck.cards
        ]
        for card in self._choose_bottom_order(remaining):
            self.player.deck.remove(card)
            self.player.deck.add(card)

        return moved_any or bool(seen)

    def _card_types(self, card):
        context = {
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
        }
        types = set(
            CardFilterEvaluator(self.game)._field_card_type(card, context)
        )
        # ``element`` and ``non_creature`` are filter helpers, not printed card
        # types.  They should not make a spell conflict with a field.
        types.discard("element")
        types.discard("non_creature")
        return types

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
