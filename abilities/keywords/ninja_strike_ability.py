"""Ninja Strike and Ura Ninja Strike keyword abilities."""

from actions.summon_action import SummonAction
from abilities.base.base_ability import BaseAbility
from core.duration_type import DurationType
from effects.base.base_effect import BaseEffect
from effects.base.enchant_effect import EnchantEffect
from events.attack_event import AttackDeclaredEvent
from events.block_event import BlockDeclaredEvent
from events.turn_event import TurnEndEvent
from zones.zone_type import ZoneType


class NinjaStrikeAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
        mana_count,
        civilizations=None,
        keyword_name="ninja_strike",
        optional=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.mana_count = int(mana_count)
        self.civilizations = civilizations
        self.keyword_name = keyword_name
        self.optional = optional
        self.event_manager = None

    def register(
        self,
        event_manager,
    ):
        self.event_manager = event_manager
        event_manager.subscribe(
            AttackDeclaredEvent,
            self.on_attack_or_block,
        )
        event_manager.subscribe(
            BlockDeclaredEvent,
            self.on_attack_or_block,
        )

    def unregister(
        self,
    ):
        if self.event_manager is None:
            return

        self.event_manager.unsubscribe(
            AttackDeclaredEvent,
            self.on_attack_or_block,
        )
        self.event_manager.unsubscribe(
            BlockDeclaredEvent,
            self.on_attack_or_block,
        )
        self.event_manager = None

    def on_attack_or_block(
        self,
        event,
    ):
        if not self._can_declare(event):
            return

        effect = NinjaStrikeSummonEffect(
            ability=self,
            event=event,
        )
        effect.source_card = self.owner_card
        effect.effect_controller = self.owner_card.owner
        self.game.effect_resolver.add_effect(
            effect,
            controller=self.owner_card.owner,
        )

    def _can_declare(
        self,
        event,
    ):
        if self.owner_card.zone != ZoneType.HAND:
            return False

        if self._attack_actor_owner(event) == self.owner_card.owner:
            return False

        attack_id = self._attack_id(event)
        return True

    def can_resolve_for_attack(
        self,
        attack_id,
    ):
        return not self._ninja_strike_used(attack_id)

    def resolve_summon(
        self,
        attack_id,
    ):
        if self.owner_card.zone != ZoneType.HAND:
            return False

        if self._ninja_strike_used(attack_id):
            return False

        if not self._mana_requirement_met():
            return False

        before_counter = self.owner_card.zone_change_counter
        self.game.action_processor.process(
            SummonAction(
                self.owner_card.owner,
                self.owner_card,
                ignore_cost=True,
            )
        )

        if (
            self.owner_card.zone == ZoneType.BATTLE
            and self.owner_card.zone_change_counter != before_counter
        ):
            self._mark_ninja_strike_used(attack_id)
            NinjaStrikeReturnEffect(
                game=self.game,
                source_card=self.owner_card,
                controller=self.owner_card.owner,
                zone_change_counter=(
                    self.owner_card.zone_change_counter
                ),
            ).resolve()
            return True

        return False

    def _mana_requirement_met(
        self,
    ):
        mana_cards = self.owner_card.owner.mana_zone.cards
        if len(mana_cards) < self.mana_count:
            return False

        if self.civilizations is None:
            return True

        return any(
            card.civilizations & self.civilizations
            for card in mana_cards
        )

    def _attack_actor_owner(
        self,
        event,
    ):
        if isinstance(
            event,
            BlockDeclaredEvent,
        ):
            return getattr(
                getattr(event, "blocker", None),
                "owner",
                None,
            )

        actor = getattr(
            event,
            "attacker",
            getattr(event, "blocker", None),
        )
        return getattr(actor, "owner", None)

    def _attack_id(
        self,
        event,
    ):
        attack_id = getattr(
            event,
            "attack_id",
            None,
        )
        if attack_id is not None:
            return attack_id

        return id(event)

    def _ninja_strike_used(
        self,
        attack_id,
    ):
        used = getattr(
            self.game.state,
            "ninja_strike_used_attack_ids",
            set(),
        )
        return (
            self.owner_card.owner,
            attack_id,
        ) in used

    def _mark_ninja_strike_used(
        self,
        attack_id,
    ):
        used = getattr(
            self.game.state,
            "ninja_strike_used_attack_ids",
            None,
        )
        if used is None:
            used = set()
            self.game.state.ninja_strike_used_attack_ids = used

        used.add(
            (
                self.owner_card.owner,
                attack_id,
            )
        )

class NinjaStrikeReturnEffect(EnchantEffect):

    def __init__(
        self,
        game,
        source_card,
        controller,
        zone_change_counter,
    ):
        super().__init__(
            source_card=source_card,
            target_card=source_card,
            duration_type=DurationType.UNTIL_END_OF_TURN,
            game=game,
            attachment_attr="temporary_ninja_strike_return_effects",
        )
        self.controller = controller
        self.zone_change_counter = zone_change_counter

    def resolve(
        self,
    ):
        self.attach()
        self.register_duration()
        self.game.event_manager.subscribe(
            TurnEndEvent,
            self.on_turn_end,
        )
        self.is_active = True
        return True

    def on_turn_end(
        self,
        event,
    ):
        if not self.is_active:
            return

        if event.player != self.controller:
            return

        return_card = self._return_candidate()
        if (
            return_card is not None
            and self._has_shinobi_race(return_card)
        ):
            moved = self.game.card_mover.move(
                card=return_card,
                owner=return_card.owner,
                from_zone=ZoneType.BATTLE,
                to_zone=ZoneType.DECK,
                reason="ninja_strike_return",
            )
            if moved:
                self._move_to_deck_bottom(return_card)

        self.unapply()

    def unapply(
        self,
    ):
        if not self.is_active:
            return

        self.game.event_manager.unsubscribe(
            TurnEndEvent,
            self.on_turn_end,
        )
        super().unapply()

    def _return_candidate(
        self,
    ):
        source_card = self.source_card
        if (
            source_card.zone == ZoneType.BATTLE
            and not getattr(
                source_card,
                "is_evolution_source",
                False,
            )
            and source_card.zone_change_counter
            == self.zone_change_counter
        ):
            return source_card

        for card in self.controller.battle_zone.cards:
            if self._contains_card(
                card,
                source_card,
            ):
                return card

        return None

    def _contains_card(
        self,
        card,
        target,
    ):
        if card is target:
            return True

        return any(
            self._contains_card(
                source,
                target,
            )
            for source in getattr(
                card,
                "evolution_sources",
                [],
            )
        )

    def _has_shinobi_race(
        self,
        card,
    ):
        races = getattr(
            card,
            "race_ja",
            (),
        )
        if isinstance(
            races,
            str,
        ):
            races = [
                races,
            ]

        return "シノビ" in {
            str(race)
            for race in races
        }

    def _move_to_deck_bottom(
        self,
        card,
    ):
        deck = card.owner.deck
        if card in deck.cards:
            deck.cards.remove(card)
            deck.cards.append(card)

    def __str__(
        self,
    ):
        return (
            "NinjaStrikeReturnEffect("
            f"{self.source_card.name})"
        )


class NinjaStrikeSummonEffect(BaseEffect):

    def __init__(
        self,
        ability,
        event,
    ):
        super().__init__()
        self.ability = ability
        self.attack_id = ability._attack_id(event)
        self.player = ability.owner_card.owner
        self.requires_trigger_declaration = True
        self.trigger_declaration_optional = ability.optional
        self.trigger_declared = False
        self.label = (
            "Ninja Strike: "
            f"{ability.owner_card.name}"
        )

    def can_resolve(
        self,
        game_state,
    ):
        return self.ability.can_resolve_for_attack(
            self.attack_id
        )

    def resolve(
        self,
    ):
        if (
            self.ability.optional
            and not getattr(
                self,
                "trigger_declared",
                False,
            )
            and not self.ability.game.choice_manager.select(
                self.player,
                [
                    True,
                    False,
                ],
                prompt=(
                    "Use Ninja Strike for "
                    f"{self.ability.owner_card.name}"
                ),
            )
        ):
            return False

        return self.ability.resolve_summon(
            self.attack_id
        )

    def __str__(
        self,
    ):
        return self.label
