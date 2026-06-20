"""Discard entire hand then draw N cards (optional).

Used for effects like "you may discard your entire hand; if you do, draw 3."
"""

from effects.base.base_effect import BaseEffect
from core.pending_cards import visible_cards
from zones.zone_type import ZoneType


class DiscardHandThenDrawEffect(BaseEffect):

    def __init__(
        self,
        player,
        draw_amount: int,
        game,
        optional: bool = True,
        prompt: str = "Discard your entire hand and draw?",
    ):
        super().__init__()
        self.player = player
        self.draw_amount = draw_amount
        self.game = game
        self.optional = optional
        self.prompt = prompt

    def resolve(self):
        hand = visible_cards(self.player.hand.cards)

        if not hand:
            return False

        if self.optional:
            confirmed = self.game.target_selector.select(
                self.player,
                [True],
                prompt=self.prompt,
                can_skip=True,
            )
            if confirmed is None:
                return False

        for card in list(hand):
            self.game.card_mover.move(
                card=card,
                owner=self.player,
                from_zone=ZoneType.HAND,
                to_zone=ZoneType.GRAVEYARD,
                reason="discard",
            )

        for _ in range(self.draw_amount):
            deck = self.player.deck.cards
            if not deck:
                break
            drawn = deck[0]
            self.game.card_mover.move(
                card=drawn,
                owner=self.player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.HAND,
                reason="draw",
            )

        return True
