"""Ability: during your turn, summon a creature from the top of your deck without paying its cost."""

from abilities.base.base_ability import BaseAbility
from actions.summon_action import SummonAction
from cards.creature_card import CreatureCard
from cards.twin_pact_card import TwinPactCard
from core.game_step import GameStep
from core.pending_cards import is_card_pending
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class SummonTopDeckCreatureAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
        max_cost=None,
        race_ja=None,
        active_zone=ZoneType.BATTLE,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.max_cost = max_cost
        self.race_ja = race_ja
        self.active_zone = active_zone
        self._used_zone_change_counter = None

    def get_play_actions(
        self,
        player,
        source_card,
    ):
        if source_card is not self.owner_card:
            return []

        if not self._can_offer_to(player):
            return []

        top_card = self._top_deck_candidate(player)
        if top_card is None:
            return []

        return [
            SummonAction(
                player,
                top_card,
                ignore_cost=True,
                play_permission=self,
                play_permissions=[self],
            )
        ]

    def can_use_for(
        self,
        player,
        card,
    ):
        if not self._can_offer_to(player):
            return False

        return card is self._top_deck_candidate(player)

    def mark_used(
        self,
        player,
        card,
    ):
        self._used_zone_change_counter = getattr(
            self.owner_card,
            "zone_change_counter",
            None,
        )

    def selection_prompt(
        self,
        player,
        card,
    ):
        return (
            f"Summon {format_card_name(card)} "
            f"from top of deck for free "
            f"({format_card_name(self.owner_card)})"
        )

    def __str__(self):
        return (
            f"{format_card_name(self.owner_card)} "
            "top-deck summon"
        )

    def _can_offer_to(self, player):
        state = self.game.state
        if state.step != GameStep.MAIN:
            return False

        if state.current_player is not player:
            return False

        if getattr(self.owner_card, "zone", None) != self.active_zone:
            return False

        if is_card_pending(self.owner_card):
            return False

        if getattr(self.owner_card, "owner", None) is not player:
            return False

        if self._has_been_used_current_instance():
            return False

        return True

    def _top_deck_candidate(self, player):
        deck = player.deck
        if not deck.cards:
            return None

        top_card = deck.cards[0]
        if is_card_pending(top_card):
            return None

        if not self._is_eligible_creature(top_card):
            return None

        return top_card

    def _is_eligible_creature(self, card):
        if not _is_creature_or_creature_face(card):
            return False

        cost = getattr(card, "cost", None)
        if isinstance(card, TwinPactCard) and card.creature_face is not None:
            cost = card.creature_face.cost

        if self.max_cost is not None and cost is not None:
            if cost > self.max_cost:
                return False

        if self.race_ja is not None:
            races = {
                str(r)
                for r in _as_list(getattr(card, "race_ja", ()))
            }
            if isinstance(card, TwinPactCard) and card.creature_face is not None:
                races |= {
                    str(r)
                    for r in _as_list(
                        getattr(card.creature_face, "race_ja", ())
                    )
                }
            if self.race_ja not in races:
                return False

        return True

    def _has_been_used_current_instance(self):
        return (
            self._used_zone_change_counter is not None
            and self._used_zone_change_counter
            == getattr(self.owner_card, "zone_change_counter", None)
        )


def build_summon_top_deck_creature_ability(spec, card, game):
    return SummonTopDeckCreatureAbility(
        owner_card=card,
        game=game,
        max_cost=spec.get("max_cost"),
        race_ja=spec.get("race_ja"),
        active_zone=ZoneType.BATTLE,
    )


def _is_creature_or_creature_face(card):
    if isinstance(card, CreatureCard):
        return True

    return (
        isinstance(card, TwinPactCard)
        and card.creature_face is not None
    )


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value] if value is not None else []
