"""Continuous trait that lets you choose creatures for your opponent."""

from abilities.active_condition import active_if_matches
from abilities.base.continuous_ability import ContinuousAbility
from effects.composition.card_predicates import is_creature_card


class OpponentCreatureChoiceReplacementAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        game,
        affected_player="opponent",
        active_if=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.affected_player = affected_player
        self.active_if = active_if

    def choice_player_for(
        self,
        player,
        options,
    ):
        if (
            not self._is_active()
            or not self._affects(player)
            or not self._is_creature_choice(options)
        ):
            return None

        return self.owner_card.owner

    def _is_active(
        self,
    ):
        return active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
            player=getattr(
                self.owner_card,
                "owner",
                None,
            ),
        )

    def _affects(
        self,
        player,
    ):
        owner = self.owner_card.owner
        if self.affected_player == "opponent":
            return player is not owner

        if self.affected_player == "controller":
            return player is owner

        if self.affected_player == "all":
            return True

        return False

    def _is_creature_choice(
        self,
        options,
    ):
        cards = [
            option
            for option in options
            if option is not None
        ]
        return bool(cards) and all(
            is_creature_card(card)
            for card in cards
        )
