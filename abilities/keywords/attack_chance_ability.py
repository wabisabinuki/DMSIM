"""Attack Chance keyword ability.

アタック・チャンス：自分の指定のクリーチャーが攻撃する時、このカード（呪文）を
コストを支払わずに実行してもよい。

実装は革命チェンジ（`revolution_change_ability`）と同型。AttackDeclaredEvent を
購読し、手札にあるこの呪文に対して、攻撃クリーチャーが指定条件に合えば
「トリガー宣言（してもよい）」付きの効果を積む。効果の解決でこの呪文を
`use(ignore_cost=True)` で踏み倒し実行する（通常の詠唱と同じく効果を積み、
解決後は墓地へ置かれる）。
"""

from abilities.base.base_ability import BaseAbility
from abilities.keywords.revolution_change_ability import (
    _normalize_attack_creature_filter,
)
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.base.base_effect import BaseEffect
from events.attack_event import AttackDeclaredEvent
from zones.zone_type import ZoneType


class AttackChanceAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
        attack_creature=None,
        optional=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.attack_creature_filter = _normalize_attack_creature_filter(
            attack_creature
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

        effect = AttackChanceEffect(
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
        attacker = getattr(
            event,
            "attacker",
            None,
        )
        return (
            self.owner_card.zone == ZoneType.HAND
            and attacker is not None
            and getattr(attacker, "owner", None)
            is self.owner_card.owner
            and getattr(event, "player", None)
            is self.owner_card.owner
            and getattr(attacker, "zone", None) == ZoneType.BATTLE
            and self.matches_attack_creature(attacker)
        )

    def matches_attack_creature(
        self,
        attacker,
    ):
        return matches_card_filter_dsl_or_legacy(
            self.game,
            attacker,
            {
                "card_type": "creature",
                **self.attack_creature_filter,
            },
            context={
                "game": self.game,
                "player": self.owner_card.owner,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
            },
            usage_type="creature",
        )


class AttackChanceEffect(BaseEffect):

    def __init__(
        self,
        ability,
        event,
    ):
        super().__init__()
        self.ability = ability
        self.player = ability.owner_card.owner
        self.requires_trigger_declaration = True
        self.trigger_declaration_optional = ability.optional
        self.trigger_declared = False
        self.label = (
            "Attack Chance: "
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
        spell = self.ability.owner_card
        if spell.zone != ZoneType.HAND:
            return False

        spell.use(
            self.ability.game,
            spell.owner,
            ignore_cost=True,
        )
        return True

    def __str__(
        self,
    ):
        return self.label


def build_attack_chance_ability(
    spec,
    card,
    game,
):
    attack_creature = spec.get(
        "attack_creature",
        spec.get(
            "attack_creature_filter",
            spec.get(
                "condition",
                spec.get("filter", {}),
            ),
        ),
    )
    if isinstance(
        attack_creature,
        dict,
    ) and "attack_creature" in attack_creature:
        attack_creature = attack_creature["attack_creature"]

    return AttackChanceAbility(
        owner_card=card,
        game=game,
        attack_creature=attack_creature,
        optional=spec.get("optional", True),
    )
