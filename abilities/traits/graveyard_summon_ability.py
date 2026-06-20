"""Grant a once-per-source normal summon from your graveyard."""

from abilities.base.base_ability import BaseAbility
from actions.summon_action import SummonAction
from cards.creature_card import CreatureCard
from cards.twin_pact_card import TwinPactCard
from core.game_step import GameStep
from core.pending_cards import is_card_pending
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class GraveyardSummonAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
        affected_player="controller",
        active_zone=ZoneType.BATTLE,
        once_per_source=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.affected_player = affected_player
        self.active_zone = _zone_type(active_zone)
        self.once_per_source = bool(once_per_source)
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

        actions = []
        for card in player.graveyard.cards:
            if not self._is_summonable_from_graveyard(
                player,
                card,
            ):
                continue

            actions.append(
                SummonAction(
                    player,
                    card,
                    play_permission=self,
                    play_permissions=[self],
                )
            )

        return actions

    def can_use_for(
        self,
        player,
        card,
    ):
        return (
            self._can_offer_to(player)
            and self._is_summonable_from_graveyard(
                player,
                card,
            )
        )

    def mark_used(
        self,
        player,
        card,
    ):
        if not self.once_per_source:
            return

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
            "Choose graveyard summon source "
            f"for {format_card_name(card)}"
        )

    def __str__(
        self,
    ):
        return (
            f"{format_card_name(self.owner_card)} "
            "graveyard summon"
        )

    def _can_offer_to(
        self,
        player,
    ):
        state = self.game.state
        if state.step != GameStep.MAIN:
            return False

        if state.current_player is not player:
            return False

        if getattr(
            self.owner_card,
            "zone",
            None,
        ) != self.active_zone:
            return False

        if is_card_pending(self.owner_card):
            return False

        if not self._affects(player):
            return False

        if self._has_been_used_current_instance():
            return False

        return True

    def _is_summonable_from_graveyard(
        self,
        player,
        card,
    ):
        return (
            getattr(card, "owner", None) is player
            and getattr(card, "zone", None) == ZoneType.GRAVEYARD
            and card in player.graveyard.cards
            and not is_card_pending(card)
            and _is_creature_or_creature_face(card)
        )

    def _affects(
        self,
        player,
    ):
        if self.affected_player in (
            "controller",
            "owner",
            "self",
        ):
            return player is self.owner_card.owner

        if self.affected_player == "opponent":
            return player is not self.owner_card.owner

        if self.affected_player == "all":
            return True

        return False

    def _has_been_used_current_instance(
        self,
    ):
        if not self.once_per_source:
            return False

        return (
            self._used_zone_change_counter
            == getattr(
                self.owner_card,
                "zone_change_counter",
                None,
            )
        )


def build_graveyard_summon_ability(
    spec,
    card,
    game,
):
    return GraveyardSummonAbility(
        owner_card=card,
        game=game,
        affected_player=spec.get(
            "affected_player",
            "controller",
        ),
        active_zone=spec.get(
            "active_zone",
            "battle",
        ),
        once_per_source=spec.get(
            "once_per_source",
            True,
        ),
    )


def _is_creature_or_creature_face(
    card,
):
    if isinstance(
        card,
        CreatureCard,
    ):
        return True

    return (
        isinstance(
            card,
            TwinPactCard,
        )
        and card.creature_face is not None
    )


def _zone_type(
    value,
):
    if isinstance(
        value,
        ZoneType,
    ):
        return value

    key = str(value).lower()
    if key in (
        "battle",
        "battle_zone",
    ):
        return ZoneType.BATTLE

    if key in (
        "grave",
        "graveyard",
    ):
        return ZoneType.GRAVEYARD

    raise ValueError(
        f"Unknown graveyard_summon active_zone: {value}"
    )
