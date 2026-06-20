"""Effect that moves cards from a deck to the graveyard."""

from effects.base.base_effect import BaseEffect
from core.pending_cards import first_visible_card
from zones.zone_type import ZoneType


class MillEffect(BaseEffect):

    def __init__(
        self,
        player,
        game,
        target="opponent_deck",
        amount=1,
        optional=False,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.target = target
        self.amount = amount
        self.optional = optional

    def can_attempt(self):
        return bool(
            first_visible_card(
                self._target_player().deck.cards
            )
        )

    def resolve(self):
        target_player = self._target_player()
        if first_visible_card(
            target_player.deck.cards
        ) is None:
            return False

        if self.optional:
            proceed = self.game.choice_manager.select(
                self.player,
                [True, False],
                prompt="Mill cards?",
            )
            if not proceed:
                return False

        moved_any = False
        for _ in range(self.amount):
            card = first_visible_card(
                target_player.deck.cards
            )
            if card is None:
                break

            moved = self.game.card_mover.move(
                card=card,
                owner=target_player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.GRAVEYARD,
                reason="mill",
            )
            moved_any = moved_any or bool(moved)

        return moved_any

    def _target_player(self):
        if self.target in (
            "own_deck",
            "controller_deck",
        ):
            return self.player

        if self.target == "opponent_deck":
            return self.game.query.get_opponent(
                self.player
            )

        raise ValueError(f"Unknown mill target: {self.target}")
