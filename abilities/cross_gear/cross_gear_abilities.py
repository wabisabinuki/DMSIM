"""クロスしたクリーチャーと連動するクロスギア用の能力群。"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.base.replacement_ability import ReplacementAbility
from abilities.base.triggered_ability import TriggeredAbility
from cards.creature_card import CreatureCard
from core.pending_cards import is_card_pending
from effects import PackagedEffect
from effects.cross_gear.cross_gear_effects import (
    FreeCrossEffect,
)
from effects.registry import build_effects
from events.attack_event import AttackDeclaredEvent
from events.battle_zone_enter_event import BattleZoneEnterEvent
from events.zone_change_attempt_event import ZoneChangeAttemptEvent
from zones.zone_type import ZoneType


class CrossGrantAbility(ContinuousAbility):
    """クロスしている間、クロス先のクリーチャーへ能力を与える。"""

    def __init__(
        self,
        owner_card,
        game=None,
        ability_ids=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.ability_ids = list(ability_ids or [])
        # id(creature) -> 付与した能力インスタンスの一覧
        self._granted = {}

    def on_cross(
        self,
        creature,
    ):
        from abilities.registry import create_ability

        granted = []
        for ability_id in self.ability_ids:
            built = create_ability(
                ability_id,
                creature,
                self.game,
            )
            abilities = (
                built
                if isinstance(built, list)
                else [built]
            )
            for ability in abilities:
                creature.abilities.append(ability)
                granted.append(ability)

        self._granted[id(creature)] = granted

    def on_uncross(
        self,
        creature,
    ):
        for ability in self._granted.pop(id(creature), []):
            if ability in creature.abilities:
                creature.abilities.remove(ability)


class CrossOnAllyEnterAbility(TriggeredAbility):
    """自分のクリーチャーが出た時、コストを支払わずそのクリーチャーにクロスしてもよい。"""

    DEFAULT_CROSS_LABEL = (
        "自分のクリーチャーが出た時、このクロスギアを"
        "コストを支払わずにそのクリーチャーにクロスしてもよい。"
    )

    def __init__(
        self,
        owner_card,
        game,
        cross=None,
        effects=None,
        label=None,
    ):
        self.owner_card = owner_card
        # Effect1: コストを支払わないクロス（任意）の設定。
        self.cross_spec = dict(cross or {})
        # Effect2 以降: クロスの後に続けて解決する汎用効果のスペック一覧（JSON 由来）。
        self.effect_specs = list(effects or [])
        self.label = label

        def condition(event):
            return (
                event.owner is self.owner_card.owner
                and event.card is not self.owner_card
                and isinstance(event.card, CreatureCard)
                and not is_card_pending(event.card)
            )

        super().__init__(
            BattleZoneEnterEvent,
            condition,
            game,
        )

    def create_effects(
        self,
        event,
    ):
        entering = event.card

        # Effect1: コストを支払わず、出たクリーチャーへクロスする（任意）。
        cross_effect = FreeCrossEffect(
            gear=self.owner_card,
            game=self.game,
            candidates=lambda: [entering],
            optional=self.cross_spec.get("optional", True),
            prompt=(
                "Cross this Cross Gear onto the entering creature for free?"
            ),
            label=self.cross_spec.get("label", self.DEFAULT_CROSS_LABEL),
        )

        # Effect2 以降: クロスの後に続けて解決する汎用効果。
        sub_effects = [
            cross_effect,
            *build_effects(
                self.effect_specs,
                self.game,
                self.owner_card.owner,
                source_card=self.owner_card,
            ),
        ]

        return [
            PackagedEffect(
                sub_effects,
                label=self.label,
            )
        ]


class CrossOnCrossedAttackAbility(TriggeredAbility):
    """クロス先のクリーチャーが攻撃する時、コストを支払わず自分の他のクリーチャーにクロスしてもよい。"""

    def __init__(
        self,
        owner_card,
        game,
        label=None,
    ):
        self.owner_card = owner_card
        self.label = label

        def condition(event):
            crossed = self.owner_card.crossed_to
            return (
                crossed is not None
                and event.attacker is crossed
            )

        super().__init__(
            AttackDeclaredEvent,
            condition,
            game,
        )

    def create_effects(
        self,
        event,
    ):
        return [
            FreeCrossEffect(
                gear=self.owner_card,
                game=self.game,
                candidates=self._other_creatures,
                optional=True,
                prompt=(
                    "Cross this Cross Gear onto another of your creatures for free?"
                ),
            )
        ]

    def _other_creatures(
        self,
    ):
        owner = self.owner_card.owner
        crossed = self.owner_card.crossed_to
        return [
            card
            for card in owner.battle_zone.cards
            if card is not self.owner_card
            and card is not crossed
            and isinstance(card, CreatureCard)
            and not is_card_pending(card)
        ]


class CrossLeaveReplacementAbility(ReplacementAbility):
    """クロス先のクリーチャーが離れる時、かわりにこのクロスギアを外してもよい。"""

    def __init__(
        self,
        owner_card,
        game,
        optional=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.optional = optional

    def applies(
        self,
        event,
    ):
        if not isinstance(event, ZoneChangeAttemptEvent):
            return False

        crossed = self.owner_card.crossed_to
        if crossed is None:
            return False

        return (
            event.card is crossed
            and event.from_zone == ZoneType.BATTLE
            and event.to_zone != ZoneType.BATTLE
            and self.owner_card.zone == ZoneType.BATTLE
            and not is_card_pending(self.owner_card)
        )

    def replace(
        self,
        event,
    ):
        if self.optional:
            proceed = self.game.choice_manager.select(
                self.owner_card.owner,
                [True, False],
                prompt="Remove this Cross Gear instead?",
            )
            if not proceed:
                return False

        # クリーチャーは離れず、かわりにクロスギアを外す。
        self.owner_card.set_crossed_to(None)
        event.cancelled = True
        return True
