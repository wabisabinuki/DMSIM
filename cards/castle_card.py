"""Castle-like cards that enter the shield zone instead of battle."""

from abilities.base.replacement_ability import ReplacementAbility
from actions.use_card_action import UseCardAction
from cards.card import Card, CardType
from core.pending_cards import begin_pending, end_pending, is_card_pending
from events.card_executed_event import CardExecutedEvent
from events.shield_break_attempt_event import ShieldBreakAttemptEvent
from events.zone_change_attempt_event import ZoneChangeAttemptEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class CastleCard(Card):

    def __init__(
        self,
        name,
        cost,
        civilizations,
        card_types=None,
        special_types=None,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):
        super().__init__(
            name=name,
            cost=cost,
            civilizations=civilizations,
            card_types=card_types or (CardType.CASTLE,),
            special_types=special_types,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )

    def can_use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if (
            not ignore_cost
            and not player.can_play(self)
        ):
            return False

        return bool(
            self._fortify_options(player)
        )

    def use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if not self.can_use(
            game,
            player,
            ignore_cost=ignore_cost,
        ):
            return False

        shield = game.target_selector.select(
            player,
            self._fortify_options(player),
            prompt=(
                "Choose a shield to fortify "
                f"with {format_card_name(self)}"
            ),
        )
        if shield is None:
            return False

        if not ignore_cost:
            try:
                play_cost = self.get_current_cost(
                    player=player,
                    game=game,
                )
            except TypeError:
                play_cost = self.get_current_cost()

            if not player.tap_mana(
                play_cost,
                spending_card=self,
                choice_manager=(
                    game.choice_manager
                ),
            ):
                return False

        from_zone = (
            getattr(
                self,
                "zone",
                None,
            )
            or ZoneType.HAND
        )
        pending_started = begin_pending(
            self,
            reason="fortify_castle",
        )

        try:
            moved = game.card_mover.move(
                card=self,
                owner=player,
                from_zone=from_zone,
                to_zone=ZoneType.SHIELD,
                reason="fortify_castle",
                shield_face_up=True,
                shield_stack_on=shield,
            )
            if moved:
                self.is_fortified_castle = True
                self.shield_face_up = True
                game.event_manager.publish(
                    CardExecutedEvent(
                        player=player,
                        card=self,
                        from_zone=from_zone,
                        ignore_cost=ignore_cost,
                    )
                )
                return True

            return False
        finally:
            if pending_started and is_card_pending(self):
                end_pending(self)

    def play_without_cost(
        self,
        game,
        player,
    ):
        return self.use(
            game,
            player,
            ignore_cost=True,
        )

    def get_available_actions(
        self,
        game,
        player,
    ):
        if self.can_use(
            game,
            player,
        ):
            return [
                UseCardAction(
                    player,
                    self,
                )
            ]

        return []

    def _fortify_options(
        self,
        player,
    ):
        fortifiable_shields = getattr(
            player.shield_zone,
            "fortifiable_shields",
            None,
        )
        if fortifiable_shields is not None:
            shields = fortifiable_shields()
        else:
            visible_shields = getattr(
                player.shield_zone,
                "visible_shields",
                None,
            )
            shields = (
                visible_shields()
                if visible_shields is not None
                else list(player.shield_zone.cards)
            )

        return [
            shield
            for shield in shields
            if shield is not self
        ]


class GalaxyCastleCard(CastleCard):

    def __init__(
        self,
        name,
        cost,
        civilizations,
        game=None,
        special_types=None,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):
        super().__init__(
            name=name,
            cost=cost,
            civilizations=civilizations,
            card_types=(CardType.CASTLE,),
            special_types=special_types,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )
        self.abilities.append(
            GalaxyCastleLeaveReplacementAbility(
                owner_card=self,
                game=game,
            )
        )

    def can_use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if ignore_cost:
            return True

        return player.can_play(self)

    def use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if not self.can_use(
            game,
            player,
            ignore_cost=ignore_cost,
        ):
            return False

        if not ignore_cost:
            try:
                play_cost = self.get_current_cost(
                    player=player,
                    game=game,
                )
            except TypeError:
                play_cost = self.get_current_cost()

            if not player.tap_mana(
                play_cost,
                spending_card=self,
                choice_manager=(
                    game.choice_manager
                ),
            ):
                return False

        from_zone = (
            getattr(
                self,
                "zone",
                None,
            )
            or ZoneType.HAND
        )
        pending_started = begin_pending(
            self,
            reason="play_galaxy_castle",
        )

        try:
            moved = game.card_mover.move(
                card=self,
                owner=player,
                from_zone=from_zone,
                to_zone=ZoneType.SHIELD,
                reason="play_galaxy_castle",
                shield_face_up=True,
            )
            if moved:
                self.is_fortified_castle = False
                self.shield_face_up = True
                game.event_manager.publish(
                    CardExecutedEvent(
                        player=player,
                        card=self,
                        from_zone=from_zone,
                        ignore_cost=ignore_cost,
                    )
                )
                return True

            return False
        finally:
            if pending_started and is_card_pending(self):
                end_pending(self)


class GalaxyCastleLeaveReplacementAbility(ReplacementAbility):

    def __init__(
        self,
        owner_card,
        game,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game

    def applies(
        self,
        event,
    ):
        if not self._is_active():
            return False

        if isinstance(
            event,
            ShieldBreakAttemptEvent,
        ):
            return event.shield_card is self.owner_card

        if isinstance(
            event,
            ZoneChangeAttemptEvent,
        ):
            return (
                event.card is self.owner_card
                and event.from_zone == ZoneType.SHIELD
                and event.to_zone != ZoneType.SHIELD
                and event.to_zone != ZoneType.GRAVEYARD
                and event.reason != "shield_break"
                and event.reason != "shield_break_replacement"
            )

        return False

    def replace(
        self,
        event,
    ):
        if isinstance(
            event,
            ShieldBreakAttemptEvent,
        ):
            moved = self.game.card_mover.move(
                card=self.owner_card,
                owner=self.owner_card.owner,
                from_zone=ZoneType.SHIELD,
                to_zone=ZoneType.GRAVEYARD,
                reason="galaxy_castle_break_replacement",
                apply_replacements=False,
            )
            if not moved:
                return False

            event.cancelled = True
            return True

        if isinstance(
            event,
            ZoneChangeAttemptEvent,
        ):
            event.to_zone = ZoneType.GRAVEYARD
            return True

        return False

    def _is_active(
        self,
    ):
        return (
            self.game is not None
            and self.owner_card.zone == ZoneType.SHIELD
            and self.owner_card.shield_face_up
            and not self.owner_card.is_fortified_castle
            and not is_card_pending(self.owner_card)
        )
