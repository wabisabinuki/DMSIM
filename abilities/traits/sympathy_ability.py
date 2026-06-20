"""Summon cost reduction based on matching friendly creatures."""

from abilities.base.continuous_ability import ContinuousAbility
from cards.creature_card import CreatureCard
from core.pending_cards import is_card_pending


class SympathyAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        scope="own_creature",
    ):
        super().__init__()
        self.owner_card = owner_card
        self.scope = scope

    def modify_cost(
        self,
        card,
        player,
        cost,
        game=None,
    ):
        if card is not self.owner_card:
            return cost

        if player is None:
            player = getattr(
                self.owner_card,
                "owner",
                None,
            )
        if player is None:
            return cost

        if self.scope not in (
            "own_creature",
            "own_creatures",
        ):
            raise ValueError(
                f"Unknown sympathy scope: {self.scope}"
            )

        reduction = sum(
            1
            for candidate in player.battle_zone.cards
            if (
                isinstance(candidate, CreatureCard)
                and not is_card_pending(candidate)
                and not getattr(
                    candidate,
                    "is_evolution_source",
                    False,
                )
            )
        )
        return max(
            1,
            cost - reduction,
        )
