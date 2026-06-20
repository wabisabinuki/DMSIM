"""
山札の上を見てカードを選び、手札に加え、残りを山札下へ戻す効果。

`filter_spec` を指定すると、手札に加える候補をその条件（例: パワー6000以上の
クリーチャー）に限定する。条件に合わないカードや選ばれなかったカードは
「残り」としてまとめて山札の下に置かれる（DM の「山札の上からN枚を表向きにし、
その中から〜を手札に加え、残りを山札の下に置く」をそのまま表す）。
"""

from effects.base.base_effect import BaseEffect
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.pending_cards import visible_cards
from zones.zone_type import ZoneType


class LookTopChooseToHandEffect(BaseEffect):

    def __init__(
        self,
        player,
        amount,
        game,
        store_as=None,
        optional=True,
        filter_spec=None,
        prompt=None,
    ):
        super().__init__()

        self.player = player
        self.amount = amount
        self.game = game
        self.store_as = store_as
        self.optional = optional
        self.filter_spec = filter_spec or {}
        self.prompt = prompt or "Choose a card to put into your hand"

    def resolve(self):
        seen = visible_cards(
            self.player.deck.cards
        )[:self.amount]

        candidates = [
            card
            for card in seen
            if self._matches(card)
        ]

        selected = None

        if candidates:
            selected = self.game.target_selector.select(
                self.player,
                candidates,
                prompt=self.prompt,
                can_skip=self.optional,
            )

        if selected is not None:
            self.game.card_mover.move(
                card=selected,
                owner=self.player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.HAND,
                reason="look_top_choose_to_hand",
            )

            print(
                f"{self.player.name} put "
                f"{selected.name} into hand"
            )

        if self.store_as:
            self.package_context[self.store_as] = selected

        remaining = [
            card
            for card in seen
            if card is not selected
            and card in self.player.deck.cards
        ]

        ordered = self._choose_bottom_order(
            remaining
        )

        for card in ordered:
            self.player.deck.remove(card)
            self.player.deck.add(card)

    def _matches(
        self,
        card,
    ):
        if not self.filter_spec:
            return True

        return matches_card_filter_dsl_or_legacy(
            self.game,
            card,
            self.filter_spec,
            context={
                "player": self.player,
                "controller": self.player,
                "source_card": self.source_card,
            },
        )

    def _choose_bottom_order(
        self,
        cards,
    ):
        if len(cards) <= 1:
            return cards

        selected = self.game.target_selector.select_multiple(
            self.player,
            cards,
            prompt="Choose order to put on bottom of deck",
            min_count=len(cards),
            max_count=len(cards),
        )

        if len(selected) != len(cards):
            return cards

        return selected
