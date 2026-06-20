"""革命0トリガー（Revolution 0 Trigger）キーワード能力。

手札の非公開領域から宣言して使う誘発型能力。ニンジャ・ストライクと同様に
``AttackDeclaredEvent`` を購読し、条件を満たせば手札のこのカードを宣言して
解決キューに積む。解決時、山札の上から1枚を表向きにし、対象条件を満たす
非進化クリーチャーなら出し、このカードをその上に進化として置く。
"""

from abilities.base.base_ability import BaseAbility
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.base.base_effect import BaseEffect
from events.attack_event import AttackDeclaredEvent
from zones.zone_type import ZoneType


DEFAULT_TARGET_FILTER = {
    "card_type": "creature",
    "civilization": "fire",
    "is_evolution": False,
}


class RevolutionZeroTriggerAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
        target_filter=None,
        optional=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.target_filter = (
            dict(target_filter)
            if target_filter
            else dict(DEFAULT_TARGET_FILTER)
        )
        self.optional = bool(optional)
        self.event_manager = None

    def register(
        self,
        event_manager,
    ):
        self.event_manager = event_manager
        event_manager.subscribe(
            AttackDeclaredEvent,
            self.on_attack_declared,
        )

    def unregister(
        self,
    ):
        if self.event_manager is None:
            return

        self.event_manager.unsubscribe(
            AttackDeclaredEvent,
            self.on_attack_declared,
        )
        self.event_manager = None

    def on_attack_declared(
        self,
        event,
    ):
        if not self.can_declare(event):
            return

        effect = RevolutionZeroEffect(
            ability=self,
            event=event,
        )
        effect.source_card = self.owner_card
        effect.effect_controller = self.owner_card.owner
        self.game.effect_resolver.add_effect(
            effect,
            controller=self.owner_card.owner,
        )

    def can_declare(
        self,
        event,
    ):
        owner = self.owner_card.owner

        # 手札の非公開領域から宣言して使う。
        if self.owner_card.zone != ZoneType.HAND:
            return False

        # 「クリーチャーが自分を攻撃する時」= プレイヤー（自分）への攻撃のみ。
        if getattr(event, "target", None) is not owner:
            return False

        if getattr(event, "attacker", None) is None:
            return False

        # 自分のシールドが1つもないこと。
        if owner.shield_zone.cards:
            return False

        return True

    def matches_target(
        self,
        card,
    ):
        return matches_card_filter_dsl_or_legacy(
            self.game,
            card,
            self.target_filter,
            context={
                "game": self.game,
                "player": self.owner_card.owner,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
            },
        )

    def resolve_reveal(
        self,
    ):
        owner = self.owner_card.owner
        rev0_card = self.owner_card

        if rev0_card.zone != ZoneType.HAND:
            return False

        deck = owner.deck
        if not deck.cards:
            return False

        # 山札の上から1枚を表向きにする（判定のための公開）。
        top_card = deck.cards[0]

        # それが対象条件を満たさなければ失敗。山札の上に残し、手札のカードも残す。
        if not self.matches_target(top_card):
            return False

        # 成功：山札の上のカードをバトルゾーンに出す（召喚ではない）。
        moved_top = self.game.card_mover.move(
            card=top_card,
            owner=owner,
            from_zone=ZoneType.DECK,
            to_zone=ZoneType.BATTLE,
            reason="revolution_zero",
            publish_battle_enter=True,
        )
        if not moved_top or top_card.zone != ZoneType.BATTLE:
            return False

        top_card.summon_turn = self.game.state.turn
        top_card.summoning_sick = True

        # その上に、革命0トリガー持ちカードを進化として置く（こちらも召喚ではない）。
        moved_self = self.game.card_mover.move(
            card=rev0_card,
            owner=owner,
            from_zone=ZoneType.HAND,
            to_zone=ZoneType.BATTLE,
            reason="revolution_zero",
            publish_battle_enter=True,
        )
        if not moved_self or rev0_card.zone != ZoneType.BATTLE:
            return False

        # 進化元として山札から出したクリーチャーを下に重ねる。
        owner.battle_zone.remove(top_card)
        rev0_card.add_evolution_source(top_card)
        top_card.zone = ZoneType.BATTLE
        top_card.owner = owner

        rev0_card.summoning_sick = False
        rev0_card.summon_turn = self.game.state.turn
        return True


class RevolutionZeroEffect(BaseEffect):

    def __init__(
        self,
        ability,
        event,
    ):
        super().__init__()
        self.ability = ability
        self.attack_id = getattr(
            event,
            "attack_id",
            None,
        )
        self.player = ability.owner_card.owner
        self.requires_trigger_declaration = True
        self.trigger_declaration_optional = ability.optional
        self.trigger_declared = False
        self.label = (
            "Revolution 0 Trigger: "
            f"{ability.owner_card.name}"
        )

    def can_resolve(
        self,
        game_state,
    ):
        return self.ability.owner_card.zone == ZoneType.HAND

    def resolve(
        self,
    ):
        return self.ability.resolve_reveal()

    def __str__(
        self,
    ):
        return self.label


def build_revolution_zero_ability(
    spec,
    card,
    game,
):
    target_filter = spec.get(
        "target",
        spec.get(
            "target_filter",
            spec.get("filter"),
        ),
    )

    # civilization のみ指定された簡易記法にも対応する。
    if target_filter is None and (
        "civilization" in spec or "civilizations" in spec
    ):
        target_filter = {
            "card_type": "creature",
            "is_evolution": False,
            "civilization": spec.get(
                "civilization",
                spec.get("civilizations"),
            ),
        }

    return RevolutionZeroTriggerAbility(
        owner_card=card,
        game=game,
        target_filter=target_filter,
        optional=spec.get("optional", True),
    )
