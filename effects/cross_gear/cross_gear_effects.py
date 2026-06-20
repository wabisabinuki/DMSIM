"""クロスギア専用の効果。コストを支払わないクロスと、相手の自クリーチャータップを扱う。"""

from cards.creature_card import CreatureCard
from core.pending_cards import is_card_pending
from effects.base.base_effect import BaseEffect
from events.card_state_event import CardTappedEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class FreeCrossEffect(BaseEffect):
    """クロスギアをコストを支払わずにクリーチャーへクロスする（任意）。"""

    def __init__(
        self,
        gear,
        game,
        candidates,
        optional=True,
        prompt=None,
        label=None,
    ):
        super().__init__()
        self.gear = gear
        self.game = game
        # candidates は callable（呼ぶと候補リスト）またはリスト。
        self.candidates = candidates
        self.optional = optional
        self.prompt = prompt
        self.label = label

    def resolve(
        self,
    ):
        gear = self.gear
        if (
            gear.zone != ZoneType.BATTLE
            or is_card_pending(gear)
        ):
            return False

        owner = gear.owner
        candidates = self._resolve_candidates()
        if not candidates:
            return False

        if self.optional:
            proceed = self.game.choice_manager.select(
                owner,
                [True, False],
                prompt=(
                    self.prompt
                    or (
                        "Cross "
                        f"{format_card_name(gear)} for free?"
                    )
                ),
            )
            if not proceed:
                return False

        target = self.game.target_selector.select(
            owner,
            candidates,
            prompt=(
                "Choose a creature to cross "
                f"{format_card_name(gear)} onto"
            ),
        )
        if target is None:
            return False

        return gear.cross(
            self.game,
            owner,
            target=target,
            ignore_cost=True,
        )

    def _resolve_candidates(
        self,
    ):
        candidates = (
            self.candidates()
            if callable(self.candidates)
            else self.candidates
        )
        return [
            card
            for card in (candidates or [])
            if card is not None
            and not is_card_pending(card)
        ]


class OpponentTapsOwnCreatureEffect(BaseEffect):
    """相手は自身のアンタップしているクリーチャーを1体選んでタップする。"""

    def __init__(
        self,
        controller,
        game,
        label=None,
    ):
        super().__init__()
        self.controller = controller
        self.game = game
        self.label = label

    def resolve(
        self,
    ):
        opponent = self._opponent()
        if opponent is None:
            return False

        candidates = [
            card
            for card in opponent.battle_zone.cards
            if isinstance(card, CreatureCard)
            and not card.tapped
            and not is_card_pending(card)
        ]
        if not candidates:
            return False

        target = self.game.target_selector.select(
            opponent,
            candidates,
            prompt="Choose one of your untapped creatures to tap",
        )
        if target is None:
            return False

        target.tapped = True
        self.game.event_manager.publish(
            CardTappedEvent(
                opponent,
                target,
                reason="effect",
            )
        )
        return True

    def _opponent(
        self,
    ):
        for player in self.game.state.players:
            if player is not self.controller:
                return player

        return None
