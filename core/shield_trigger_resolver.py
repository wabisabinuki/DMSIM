"""
シールドチェックで公開されたS・トリガーとG・ストライクの
宣言・解決処理を扱うリゾルバー。
"""

from dataclasses import dataclass

from ui.trigger_debug import (
    log_g_strike_play,
    log_shield_trigger_play,
)

from actions.cast_spell_action import CastSpellAction
from actions.summon_action import SummonAction
from cards.card import CardType
from cards.twin_pact_card import TwinPactCard
from core.duration_type import DurationType
from effects.combat.temporary_combat_restriction_effect import (
    TemporaryCombatRestrictionEffect,
)


SHIELD_TRIGGER = "shield_trigger"
G_STRIKE = "g_strike"


@dataclass(eq=False)
class ShieldCheckItem:
    kind: str
    card: object
    ability: object = None

    @property
    def owner(
        self,
    ):
        return self.card.owner

    @property
    def name(
        self,
    ):
        return self.card.name

    @property
    def label(
        self,
    ):
        if self.kind == G_STRIKE:
            return f"G・ストライク: {self.card.name}"

        return f"S・トリガー: {self.card.name}"

    def __eq__(
        self,
        other,
    ):
        return other is self or other is self.card

    def __str__(
        self,
    ):
        return self.label


class ShieldTriggerResolver:

    def __init__(
        self,
        context,
    ):

        self.context = context

        self.pending_items = []

    @property
    def pending_cards(
        self,
    ):
        return [
            item.card
            for item in self.pending_items
        ]

    @pending_cards.setter
    def pending_cards(
        self,
        cards,
    ):
        self.pending_items = [
            self._coerce_item(card)
            for card in cards
        ]

    def enqueue(
        self,
        card,
    ):

        self.pending_items.append(
            ShieldCheckItem(
                SHIELD_TRIGGER,
                card,
            )
        )

    def enqueue_g_strike(
        self,
        card,
        ability=None,
    ):

        self.pending_items.append(
            ShieldCheckItem(
                G_STRIKE,
                card,
                ability=ability,
            )
        )

    def declare_triggers(
        self,
        player,
    ):

        if not self.pending_items:
            return

        player_items = [
            item
            for item in self.pending_items
            if item.owner == player
            and self._can_declare(
                player,
                item,
            )
        ]

        if not player_items:
            self.pending_items = [
                item
                for item in self.pending_items
                if item.owner != player
            ]
            return

        selected = (
            self.context
            .choice_manager
            .select(
                player,
                player_items,
                prompt=(
                    "Choose shield checks "
                    "to declare"
                ),
                min_count=0,
                max_count=len(player_items),
            )
        )
        selected = self._selected_items(
            selected,
            player_items,
        )

        self.pending_items = (
            [
                item
                for item in self.pending_items
                if item.owner != player
            ]
            + selected
        )

    def resolve_for_player(
        self,
        player,
    ):

        self.declare_triggers(
            player
        )
        self.resolve()

    def has_pending_for(
        self,
        player,
    ):

        return any(
            item.owner == player
            for item in self.pending_items
        )

    def resolve(
        self,
    ):

        ctx = self.context
        controller = ctx.controller

        while self.pending_items:

            choices = (
                self._next_priority_items()
            )

            owner = choices[0].owner

            selected = (
                ctx.choice_manager.select(
                    owner,
                    choices,
                    (
                        "Choose shield check "
                        "to resolve"
                    ),
                )
            )
            item = self._selected_item(
                selected,
                choices,
            )
            if item is None:
                item = choices[0]

            self.pending_items.remove(
                item
            )

            if item.kind == G_STRIKE:
                self._resolve_g_strike(
                    item,
                )
                continue

            self._resolve_shield_trigger(
                item,
                controller,
            )

        ctx.game_loop.resolve()

    def _resolve_shield_trigger(
        self,
        item,
        controller,
    ):

        ctx = self.context
        owner = item.owner
        card = item.card

        if not self._can_play_shield_trigger(
            owner,
            card,
        ):
            return

        log_shield_trigger_play(card)

        previous = ctx.resolving_shield_trigger
        ctx.resolving_shield_trigger = True

        try:
            card.play_without_cost(
                controller,
                card.owner,
            )
        finally:
            ctx.resolving_shield_trigger = previous

    def _resolve_g_strike(
        self,
        item,
    ):

        ctx = self.context
        card = item.card
        opponent = ctx.query.get_opponent(
            card.owner
        )

        if opponent is None:
            log_g_strike_play(
                card,
            )
            return

        target = ctx.target_selector.select(
            card.owner,
            ctx.query.get_selectable_creatures(
                source=card,
                controller=opponent,
            ),
            prompt="Choose an opponent creature for G・ストライク",
            can_skip=True,
        )

        if target is None:
            log_g_strike_play(
                card,
            )
            return

        effect = TemporaryCombatRestrictionEffect(
            game=ctx,
            source_card=card,
            target_card=target,
            restrictions=["attack"],
            duration_type=DurationType.UNTIL_END_OF_TURN,
        )
        effect.resolve()
        log_g_strike_play(
            card,
            target,
        )

    def _next_priority_items(
        self,
    ):

        group_key = min(
            self._priority_key(item)
            for item in self.pending_items
        )

        return [
            item
            for item in self.pending_items
            if self._priority_key(item) == group_key
        ]

    def _priority_key(
        self,
        item,
    ):

        players = self.context.state.players
        turn_index = (
            self.context
            .state
            .turn_player_index
        )

        if item.owner not in players:
            return len(players)

        owner_index = players.index(
            item.owner
        )

        return (
            owner_index - turn_index
        ) % len(players)

    def _can_declare(
        self,
        player,
        item,
    ):

        if item.kind == G_STRIKE:
            return True

        return self._can_play_shield_trigger(
            player,
            item.card,
        )

    def _selected_items(
        self,
        selected,
        choices,
    ):

        if selected is None:
            return []

        if not isinstance(
            selected,
            list,
        ):
            selected = [
                selected,
            ]

        result = []
        remaining = list(choices)
        for value in selected:
            item = self._selected_item(
                value,
                remaining,
            )
            if item is None:
                continue

            result.append(item)
            remaining.remove(item)

        return result

    def _selected_item(
        self,
        selected,
        choices,
    ):

        if isinstance(
            selected,
            ShieldCheckItem,
        ):
            return selected if selected in choices else None

        for item in choices:
            if item == selected:
                return item

        return None

    def _coerce_item(
        self,
        value,
    ):

        if isinstance(
            value,
            ShieldCheckItem,
        ):
            return value

        return ShieldCheckItem(
            SHIELD_TRIGGER,
            value,
        )

    def _can_play_shield_trigger(
        self,
        player,
        card,
    ):

        if getattr(
            card,
            "s_trigger_suppressed",
            False,
        ):
            return False

        action = self._shield_trigger_action(
            player,
            card,
        )

        if action is None:
            return False

        if isinstance(
            action,
            _UnvalidatedShieldTriggerAction,
        ):
            return True

        return self.context.action_validator.validate(
            action
        )

    def _shield_trigger_action(
        self,
        player,
        card,
    ):

        if isinstance(card, TwinPactCard):
            original_face = card.selected_face
            selected = card._select_shield_trigger_face()
            if not selected:
                return None

            action = self._action_for_selected_card(
                player,
                card,
            )
            card.selected_face = original_face
            card._bind_selected_face_abilities()
            return action

        if CardType.SPELL in self._card_types(card):
            return CastSpellAction(
                player=player,
                spell=card,
                ignore_cost=True,
            )

        if CardType.CREATURE in self._card_types(card):
            return SummonAction(
                player=player,
                card=card,
                ignore_cost=True,
            )

        if hasattr(
            card,
            "play_without_cost",
        ):
            return _UnvalidatedShieldTriggerAction()

        return None

    def _action_for_selected_card(
        self,
        player,
        card,
    ):

        if CardType.SPELL in self._card_types(
            card.selected_face
        ):
            return CastSpellAction(
                player=player,
                spell=card,
                ignore_cost=True,
            )

        if CardType.CREATURE in self._card_types(
            card.selected_face
        ):
            return SummonAction(
                player=player,
                card=card,
                ignore_cost=True,
            )

        return None

    def _card_types(
        self,
        card,
    ):

        card_types = getattr(
            card,
            "card_types",
            (),
        )
        if isinstance(
            card_types,
            CardType,
        ):
            return (card_types,)

        return tuple(card_types)


class _UnvalidatedShieldTriggerAction:
    pass
