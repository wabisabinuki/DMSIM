"""Revolution Change keyword ability."""

from abilities.base.base_ability import BaseAbility
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.card_mover import SwapMove
from effects.base.base_effect import BaseEffect
from events.attack_event import AttackDeclaredEvent
from zones.zone_type import ZoneType


class RevolutionChangeAbility(BaseAbility):

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

        effect = RevolutionChangeEffect(
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


class RevolutionChangeEffect(BaseEffect):

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
        self.event_attacker = getattr(
            event,
            "attacker",
            None,
        )
        self.player = ability.owner_card.owner
        self.requires_trigger_declaration = True
        self.trigger_declaration_optional = ability.optional
        self.trigger_declared = False
        self.label = (
            "Revolution Change: "
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
        attacker = self._current_attacker()
        change_card = self.ability.owner_card

        if attacker is None:
            return False

        if attacker.zone != ZoneType.BATTLE:
            return False

        if change_card.zone != ZoneType.HAND:
            return False

        if not self.ability.matches_attack_creature(attacker):
            return False

        inherited_tapped = bool(
            getattr(
                attacker,
                "tapped",
                False,
            )
        )

        result = self.ability.game.card_mover.swap(
            SwapMove(
                card=attacker,
                owner=attacker.owner,
                from_zone=ZoneType.BATTLE,
                to_zone=ZoneType.HAND,
                reason="revolution_change",
            ),
            SwapMove(
                card=change_card,
                owner=change_card.owner,
                from_zone=ZoneType.HAND,
                to_zone=ZoneType.BATTLE,
                reason="revolution_change",
            ),
        )
        if not result:
            return False

        change_card.tapped = inherited_tapped
        change_card.summon_turn = self.ability.game.state.turn
        change_card.summoning_sick = False
        self._inherit_attack_state(change_card)
        return True

    def _current_attacker(
        self,
    ):
        state = self.ability.game.state
        current_attack_id = getattr(
            state,
            "current_attack_id",
            None,
        )
        if (
            self.attack_id is not None
            and current_attack_id == self.attack_id
        ):
            candidate = getattr(
                state,
                "current_attacker",
                None,
            )
        elif current_attack_id is None:
            candidate = self.event_attacker
        else:
            candidate = None

        # 革命チェンジが参照できるのは、攻撃を宣言したクリーチャー（および
        # そこから進化・退化したクリーチャー）だけ。別の革命チェンジで一度
        # 入れ替わると、宣言したクリーチャーはバトルゾーンを離れて対象が
        # いなくなった扱いになるため、入れ替わった後のクリーチャーには
        # 連鎖しない。
        if not self._is_declared_attacker(candidate):
            return None

        return candidate

    def _is_declared_attacker(
        self,
        candidate,
    ):
        original = self.event_attacker
        if candidate is None or original is None:
            return False

        if candidate is original:
            return True

        # 進化（candidate の進化元に original がいる）／
        # 退化（original の進化元に candidate がいる）の系譜なら同一とみなす。
        return self._contains_in_evolution(
            candidate,
            original,
        ) or self._contains_in_evolution(
            original,
            candidate,
        )

    def _contains_in_evolution(
        self,
        card,
        target,
    ):
        for source in getattr(
            card,
            "evolution_sources",
            [],
        ):
            if source is target or self._contains_in_evolution(
                source,
                target,
            ):
                return True

        return False

    def _inherit_attack_state(
        self,
        new_attacker,
    ):
        state = self.ability.game.state
        if (
            self.attack_id is not None
            and getattr(
                state,
                "current_attack_id",
                None,
            ) != self.attack_id
        ):
            return

        state.current_attacker = new_attacker

    def __str__(
        self,
    ):
        return self.label


def build_revolution_change_ability(
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

    return RevolutionChangeAbility(
        owner_card=card,
        game=game,
        attack_creature=attack_creature,
        optional=spec.get("optional", True),
    )


def _normalize_attack_creature_filter(
    filter_spec,
):
    filter_spec = dict(filter_spec or {})

    if "race" in filter_spec and "race_ja" not in filter_spec:
        filter_spec["race_ja"] = filter_spec.pop("race")

    if "races" in filter_spec and "race_ja" not in filter_spec:
        filter_spec["race_ja"] = filter_spec.pop("races")

    for key in (
        "civilization",
        "civilizations",
    ):
        value = filter_spec.get(key)
        if isinstance(
            value,
            list,
        ):
            filter_spec[key] = {
                "in": value,
            }

    return filter_spec
