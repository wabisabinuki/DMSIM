"""Factory for v2 JSON effect specs keyed by ``type``."""

from actions.attack_creature_action import AttackCreatureAction
from cards.card import Card
from cards.twin_pact_card import TwinPactCard
from core.card_filter_evaluator import CardFilterEvaluator
from core.choice_manager import ChoiceOption
from core.condition_evaluator import ConditionEvaluator
from core.effect_argument_resolver import (
    EffectArgumentResolver,
    parse_duration_spec,
)
from effects.base.base_effect import BaseEffect
from effects.combat.tap_effect import TapEffect
from effects.combat.temporary_combat_restriction_effect import (
    TemporaryCombatRestrictionEffect,
)
from effects.combat.untap_effect import UntapEffect
from effects.effect_context import EffectContext, ref_to_stored_spec
from effects.modifiers.add_power_modifier_effect import AddPowerModifierEffect
from effects.modifiers.battle_scoped_power_modifier_effect import (
    BattleScopedPowerModifierEffect,
)
from effects.modifiers.timed_power_modifier_effect import (
    TimedPowerModifierEffect,
)
from effects.registry import build_effects
from effects.zones.dectroy_effect import DestroyEffect
from zones.zone_type import ZoneType


V2_EFFECT_BUILDERS = {
    "draw": "_build_legacy_effect",
    "discard": "_build_legacy_effect",
    "execute": "_build_execute_effect",
    "move": "_build_move_effect",
    "select": "_build_select_effect",
    "destroy": "_build_target_effect",
    "tap": "_build_target_effect",
    "untap": "_build_target_effect",
    "modify_power": "_build_target_effect",
    "temporary_combat_restriction": "_build_target_effect",
    "battle": "_build_battle_effect",
    "if": "_build_if_effect",
    "choice": "_build_choice_effect",
    "choose_number": "_build_choose_number_effect",
    "alternative_effect": "_build_alternative_effect",
}

V2_EFFECT_TYPES = frozenset(V2_EFFECT_BUILDERS)

LEGACY_EFFECT_IDS = {
    "discard": "discard",
    "draw": "draw",
    "move": "move_card",
}


class EffectFactory:
    """Build concrete Effect objects from v2 effect specs."""

    BUILDERS = V2_EFFECT_BUILDERS

    LEGACY_SPEC_ADJUSTERS = {
        "execute": "_adjust_execute_legacy_spec",
        "move": "_adjust_move_legacy_spec",
    }

    def __init__(
        self,
        game,
    ):
        self.game = game

    def build_many(
        self,
        specs,
        player,
        source_card=None,
    ):
        effects = []

        for spec in _as_list(specs):
            effect = self.build(
                spec,
                player,
                source_card=source_card,
            )
            if effect is None:
                continue
            if isinstance(
                effect,
                list,
            ):
                effects.extend(effect)
            else:
                effects.append(effect)

        return effects

    def build(
        self,
        spec,
        player,
        source_card=None,
    ):
        if (
            ("id" in spec or "effect_id" in spec)
            and spec.get("type") not in V2_EFFECT_TYPES
        ):
            return build_effects(
                [spec],
                self.game,
                player,
                source_card=source_card,
            )

        effect_type = spec.get("type")
        builder_name = self.BUILDERS.get(effect_type)
        if builder_name is not None:
            effect = getattr(self, builder_name)(
                spec,
                player,
                source_card,
            )
            return self._attach_package_connector(
                effect,
                spec,
            )

        raise ValueError(
            f"Unknown v2 effect type: {effect_type}"
        )

    def _attach_package_connector(
        self,
        effect,
        spec,
    ):
        connector = spec.get(
            "connector",
            spec.get("package_connector"),
        )
        if connector is None or effect is None:
            return effect

        if isinstance(
            effect,
            list,
        ):
            for item in effect:
                item.package_connector = connector
            return effect

        effect.package_connector = connector
        return effect

    def _build_legacy_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return build_effects(
            [
                self._legacy_spec(
                    spec,
                    source_card,
                )
            ],
            self.game,
            player,
            source_card=source_card,
        )

    def _build_execute_effect(
        self,
        spec,
        player,
        source_card,
    ):
        if self._has_explicit_cards(spec):
            return V2ExecuteEffect(
                spec,
                self.game,
                player,
                source_card,
            )

        return self._build_legacy_effect(
            spec,
            player,
            source_card,
        )

    def _build_move_effect(
        self,
        spec,
        player,
        source_card,
    ):
        if self._has_explicit_cards(spec):
            return V2MoveEffect(
                spec,
                self.game,
                player,
                source_card,
            )

        return self._build_legacy_effect(
            spec,
            player,
            source_card,
        )

    def _build_select_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2SelectEffect(
            spec,
            self.game,
            player,
            source_card,
        )

    def _build_target_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2TargetEffect(
            spec,
            self.game,
            player,
            source_card,
        )

    def _build_battle_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2BattleEffect(
            spec,
            self.game,
            player,
            source_card,
        )

    def _build_if_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2IfEffect(
            spec,
            self,
            player,
            source_card,
        )

    def _build_choice_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2ChoiceEffect(
            spec,
            self,
            player,
            source_card,
        )

    def _build_choose_number_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2ChooseNumberEffect(
            spec,
            self.game,
            player,
        )

    def _build_alternative_effect(
        self,
        spec,
        player,
        source_card,
    ):
        return V2AlternativeEffect(
            spec,
            self,
            player,
            source_card,
        )

    def _legacy_spec(
        self,
        spec,
        source_card,
    ):
        effect_type = spec["type"]
        legacy = {
            key: ref_to_stored_spec(value)
            for key, value in spec.items()
            if key != "type"
        }

        legacy["id"] = LEGACY_EFFECT_IDS.get(effect_type, effect_type)
        adjuster_name = self.LEGACY_SPEC_ADJUSTERS.get(effect_type)
        if adjuster_name is not None:
            getattr(self, adjuster_name)(
                spec,
                legacy,
            )

        if source_card is not None:
            legacy["source_card"] = source_card

        return legacy

    def _adjust_execute_legacy_spec(
        self,
        spec,
        legacy,
    ):
        from_zone = spec.get(
            "from_zone",
            spec.get("source_zone", "hand"),
        )
        legacy["id"] = (
            "execute_card_from_hand"
            if from_zone in (
                None,
                "hand",
                "hand_zone",
            )
            else "execute_card_from_zone"
        )

    def _adjust_move_legacy_spec(
        self,
        spec,
        legacy,
    ):
        if "from" in spec and "from_zone" not in legacy:
            legacy["from_zone"] = spec["from"]
        if "to" in spec and "to_zone" not in legacy:
            legacy["to_zone"] = spec["to"]

    def _has_explicit_cards(
        self,
        spec,
    ):
        return any(
            key in spec
            for key in (
                "card",
                "cards",
                "target",
            )
        )


class V2SelectEffect(BaseEffect):
    """Select cards and store the result for later ``ref`` lookups."""

    CANDIDATE_HANDLERS = {
        "creatures": "_candidate_creatures",
        "all_creatures": "_candidate_creatures",
        "opponent_creatures": "_candidate_opponent_creatures",
        "own_creatures": "_candidate_own_creatures",
        "own_other_creatures": "_candidate_own_other_creatures",
        "opponent_battle_zone": "_candidate_opponent_battle",
        "opponent_battle": "_candidate_opponent_battle",
        "own_battle_zone": "_candidate_own_battle",
        "own_battle": "_candidate_own_battle",
    }

    def __init__(
        self,
        spec,
        game,
        player,
        source_card,
    ):
        super().__init__()
        self.spec = spec
        self.game = game
        self.player = player
        self.source_card = source_card
        self.args = EffectArgumentResolver(game)

    def can_attempt(
        self,
    ):
        return bool(self._options())

    def resolve(
        self,
    ):
        options = self._options()
        if not options:
            return False

        count = self._count(options)
        optional = self.spec.get("optional", True)
        prompt = self.spec.get("prompt", "Choose a target")

        if count == 1:
            selected = self.game.target_selector.select(
                self._selector_player(),
                options,
                prompt=prompt,
                can_skip=optional,
            )
        else:
            selected = self.game.target_selector.select_multiple(
                self._selector_player(),
                options,
                prompt=prompt,
                min_count=0 if optional else count,
                max_count=count,
                can_skip=optional,
            )

        if not selected:
            return False

        store_as = self.spec.get("store_as")
        if store_as:
            EffectContext.from_package_context(
                self.package_context
            ).store(
                store_as,
                selected,
            )

        return True

    def _options(
        self,
    ):
        filter_spec = self.spec.get("filter", {})
        evaluator = CardFilterEvaluator(
            self.game
        )
        return [
            card
            for card in self._candidates()
            if evaluator.matches(
                card,
                filter_spec,
                self._filter_context(),
            )
        ]

    def _candidates(
        self,
    ):
        candidates = self.spec.get(
            "candidates",
            self.spec.get("from", self.spec.get("from_zone")),
        )

        if isinstance(
            candidates,
            dict,
        ):
            return self._zone_cards(candidates)

        handler_name = self.CANDIDATE_HANDLERS.get(candidates)
        if handler_name is not None:
            return getattr(self, handler_name)()

        if candidates is not None:
            return self._zone_cards(
                {
                    "zone": candidates,
                    "player": self.spec.get("player", "self"),
                }
            )

        raise ValueError(
            f"Unknown v2 select candidates: {candidates}"
        )

    def _candidate_creatures(
        self,
    ):
        return self.game.query.get_selectable_creatures(
            source=self.source_card or self.player,
        )

    def _candidate_opponent_creatures(
        self,
    ):
        opponent = self.game.query.get_opponent(
            self.player
        )
        return self.game.query.get_selectable_creatures(
            source=self.source_card or self.player,
            controller=opponent,
        )

    def _candidate_own_creatures(
        self,
    ):
        return self.game.query.get_selectable_creatures(
            source=self.source_card or self.player,
            controller=self.player,
        )

    def _candidate_own_other_creatures(
        self,
    ):
        return [
            card
            for card in self._candidate_own_creatures()
            if card is not self.source_card
        ]

    def _candidate_opponent_battle(
        self,
    ):
        return self.game.query.get_battle_cards(
            controller=self.game.query.get_opponent(
                self.player
            )
        )

    def _candidate_own_battle(
        self,
    ):
        return self.game.query.get_battle_cards(
            controller=self.player,
        )

    def _zone_cards(
        self,
        spec,
    ):
        context = self.args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        player = self.args.player(
            spec.get("player", "self"),
            context,
        )
        zone = self.args.zone(
            spec.get("zone"),
            context,
        )
        player_zone = player.get_zone(zone)
        visible_shields = getattr(
            player_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(
            player_zone.cards
        )

    def _count(
        self,
        options=None,
    ):
        raw_count = self.spec.get(
            "count",
            self.spec.get("amount", 1),
        )
        if raw_count in (
            "all",
            "any",
            "up_to_all",
        ):
            return len(options or self._options())

        context = EffectContext.from_package_context(
            self.package_context
        )
        return int(
            context.resolve(
                raw_count
            )
        )

    def _filter_context(
        self,
    ):
        return {
            **self.package_context,
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
            "source_info": self.source_info,
        }

    def _selector_player(
        self,
    ):
        context = self.args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        return self.args.player(
            self.spec.get(
                "selector",
                self.spec.get("choosing_player", "self"),
            ),
            context,
        )


class V2TargetEffect(BaseEffect):
    """Apply a simple operation to self, a stored ref, or explicit card objects."""

    APPLY_HANDLERS = {
        "destroy": "_apply_destroy",
        "tap": "_apply_tap",
        "untap": "_apply_untap",
        "modify_power": "_apply_modify_power",
        "temporary_combat_restriction": "_apply_temporary_combat_restriction",
    }

    def __init__(
        self,
        spec,
        game,
        player,
        source_card,
    ):
        super().__init__()
        self.spec = spec
        self.game = game
        self.player = player
        self.source_card = source_card
        self.args = EffectArgumentResolver(game)

    def can_attempt(
        self,
    ):
        return bool(self._targets())

    def resolve(
        self,
    ):
        targets = self._targets()
        if not targets:
            return False

        attempted = False
        for target in targets:
            attempted = self._apply(target) or attempted

        store_as = self.spec.get("store_as")
        if store_as:
            EffectContext.from_package_context(
                self.package_context
            ).store(
                store_as,
                targets[0] if len(targets) == 1 else targets,
            )

        return attempted

    def _targets(
        self,
    ):
        context = self.args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        value = self.spec.get(
            "cards",
            self.spec.get(
                "card",
                self.spec.get("target", "self"),
            ),
        )
        return self.args.cards(
            value,
            context,
        )

    def _apply(
        self,
        target,
    ):
        effect_type = self.spec["type"]
        handler_name = self.APPLY_HANDLERS.get(effect_type)
        if handler_name is not None:
            return getattr(self, handler_name)(target)

        raise ValueError(
            f"Unknown v2 target effect type: {effect_type}"
        )

    def _apply_destroy(
        self,
        target,
    ):
        DestroyEffect(
            target=target,
            game=self.game,
        ).resolve()
        return True

    def _apply_tap(
        self,
        target,
    ):
        return TapEffect(
            target=target,
            game=self.game,
        ).resolve()

    def _apply_untap(
        self,
        target,
    ):
        return UntapEffect(
            target=target,
            game=self.game,
            player=self.player,
        ).resolve()

    def _apply_temporary_combat_restriction(
        self,
        target,
    ):
        effect = TemporaryCombatRestrictionEffect(
            game=self.game,
            source_card=self.source_card,
            target_card=target,
            restrictions=self.spec.get("restrictions", []),
            duration_type=parse_duration_spec(
                self.spec.get("duration")
            ),
        )
        effect.package_context = self.package_context
        effect.resolve()
        return True

    def _apply_modify_power(
        self,
        target,
    ):
        amount = EffectContext.from_package_context(
            self.package_context
        ).resolve(
            self.spec.get("amount", self.spec.get("value", 0))
        )
        duration = _duration_key(
            self.spec.get("duration")
        )
        if duration in (
            "until_battle_end",
            "until_end_of_battle",
            "battle_end",
        ):
            event = self.package_context.get("event")
            return BattleScopedPowerModifierEffect(
                source_card=self.source_card,
                target_card=target,
                amount=amount,
                game=self.game,
                battle_id=getattr(event, "battle_id", None),
            ).resolve()

        if duration is not None:
            TimedPowerModifierEffect(
                source_card=self.source_card,
                target_card=target,
                modifier_amount=amount,
                duration_type=self.args.duration(
                    self.spec.get("duration")
                ),
                game=self.game,
            ).resolve()
            return True

        AddPowerModifierEffect(
            target=target,
            amount=amount,
        ).resolve()
        return True


class V2ExecuteEffect(BaseEffect):
    """Execute explicit cards, including cards retrieved through ``ref``."""

    def __init__(
        self,
        spec,
        game,
        player,
        source_card,
    ):
        super().__init__()
        self.spec = spec
        self.game = game
        self.player = player
        self.source_card = source_card
        self.args = EffectArgumentResolver(game)

    def can_attempt(
        self,
    ):
        return bool(self._targets())

    def resolve(
        self,
    ):
        attempted = False
        for card in self._targets():
            if card is None or type(card).use is Card.use:
                continue

            self._prepare_card_for_execution(card)
            before_zone = getattr(
                card,
                "zone",
                None,
            )
            before_counter = getattr(
                card,
                "zone_change_counter",
                None,
            )
            owner = getattr(
                card,
                "owner",
                self.player,
            )
            card.use(
                self.game,
                owner,
                ignore_cost=_ignore_cost(self.spec),
            )
            attempted = attempted or (
                getattr(card, "zone", None) != before_zone
                or getattr(card, "zone_change_counter", None)
                != before_counter
            )

        return attempted

    def _targets(
        self,
    ):
        context = self.args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        value = self.spec.get(
            "cards",
            self.spec.get(
                "card",
                self.spec.get("target"),
            ),
        )
        return self.args.cards(
            value,
            context,
        )

    def _prepare_card_for_execution(
        self,
        card,
    ):
        if not isinstance(card, TwinPactCard):
            return

        usage_type = self.spec.get(
            "card_type",
            self.spec.get("type"),
        )
        if usage_type is None:
            usage_type = self._usage_type_from_target_filter()

        key = (
            str(usage_type).lower()
            if usage_type is not None
            else None
        )
        if key in (
            "creature",
            "element",
        ):
            card.select_creature_face()
            return

        if key in (
            "spell",
            "non_creature",
        ):
            card.select_spell_face()

    def _usage_type_from_target_filter(
        self,
    ):
        target_filter = self.spec.get("filter", {})
        card_type = target_filter.get("card_type")
        if isinstance(card_type, str):
            return card_type

        not_filter = target_filter.get("not")
        if isinstance(not_filter, dict):
            if not_filter.get("card_type") == "creature":
                return "non_creature"

        return None


class V2BattleEffect(BaseEffect):
    """Force two referenced creatures to battle each other.

    ``attacker`` / ``defender`` は ``{"ref": ...}`` などで解決する単一の
    クリーチャー参照。攻撃側を省略した場合は発生源（``self``）を用いる。
    防御側が未解決（直前の任意選択がスキップされた等）の場合は何もしない。
    """

    def __init__(
        self,
        spec,
        game,
        player,
        source_card,
    ):
        super().__init__()
        self.spec = spec
        self.game = game
        self.player = player
        self.source_card = source_card
        self.args = EffectArgumentResolver(game)

    def resolve(
        self,
    ):
        attacker = self._resolve_card(
            self.spec.get("attacker", "self")
        )
        defender = self._resolve_card(
            self.spec.get("defender")
        )
        if (
            attacker is None
            or defender is None
            or attacker is defender
        ):
            return False

        self.game.combat_manager.process_battle(
            AttackCreatureAction(
                attacker.owner,
                attacker,
                defender,
            )
        )
        return True

    def _resolve_card(
        self,
        value,
    ):
        if value is None:
            return None

        context = self.args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        cards = self.args.cards(
            value,
            context,
        )
        return cards[0] if cards else None


class V2MoveEffect(BaseEffect):
    """Move explicit cards, including cards retrieved through ``ref``."""

    def __init__(
        self,
        spec,
        game,
        player,
        source_card,
    ):
        super().__init__()
        self.spec = spec
        self.game = game
        self.player = player
        self.source_card = source_card
        self.args = EffectArgumentResolver(game)

    def resolve(
        self,
    ):
        context = self.args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        cards = self.args.cards(
            self.spec.get(
                "cards",
                self.spec.get(
                    "card",
                    self.spec.get("target"),
                ),
            ),
            context,
        )
        if not cards:
            return False

        if self.spec.get("optional", False) and not self._confirm():
            return False

        to_zone = self.args.zone(
            self.spec.get(
                "to_zone",
                self.spec.get("to"),
            ),
            context,
        )
        moved = []

        for card in cards:
            if card is None:
                continue
            owner = getattr(
                card,
                "owner",
                self.player,
            )
            from_zone = self.args.zone(
                self.spec.get(
                    "from_zone",
                    self.spec.get(
                        "from",
                        getattr(card, "zone", None),
                    ),
                ),
                context,
            )
            # from_zone を明示した移動では、解決時にカードが既にその領域を
            # 離れていたら何もしない（「そのクリーチャーを墓地から〜」等）。
            if getattr(card, "zone", None) != from_zone:
                continue
            shield_stack_on = self._shield_stack_on(
                owner,
                to_zone,
                context,
            )
            if (
                self._requires_shield_stack(to_zone)
                and shield_stack_on is None
            ):
                continue

            if self.game.card_mover.move(
                card=card,
                owner=owner,
                from_zone=from_zone,
                to_zone=to_zone,
                reason=self.spec.get("reason", "move"),
                shield_stack_on=shield_stack_on,
            ):
                moved.append(card)
                self._position_in_destination(
                    card,
                    owner,
                    to_zone,
                )

        store_as = self.spec.get("store_as")
        if store_as:
            context["effect_context"].store(
                store_as,
                moved[0] if len(moved) == 1 else moved,
            )

        return bool(moved)

    def _confirm(
        self,
    ):
        return bool(
            self.game.choice_manager.select(
                self.player,
                [
                    True,
                    False,
                ],
                prompt=self.spec.get(
                    "prompt",
                    "Move the card?",
                ),
            )
        )

    def _position_in_destination(
        self,
        card,
        owner,
        to_zone,
    ):
        position = self.spec.get("destination_position")
        if position != "top":
            return

        destination = owner.get_zone(to_zone)
        if card in destination.cards:
            destination.cards.remove(card)
            destination.cards.insert(
                0,
                card,
            )

    def _shield_stack_on(
        self,
        owner,
        to_zone,
        context,
    ):
        if not self._requires_shield_stack(to_zone):
            return None

        # 重ね先スロットを ref で固定できる（例: {"ref": "source"} で
        # 「このシールドの下に置く」）。スロットが見つからなければ移動しない。
        explicit = self.spec.get(
            "shield_stack_on",
            self.spec.get("stack_on"),
        )
        if explicit is not None:
            resolved = self.args.value(
                explicit,
                context,
            )
            if (
                resolved is not None
                and resolved in owner.shield_zone.cards
            ):
                return resolved
            return None

        visible_shields = getattr(
            owner.shield_zone,
            "visible_shields",
            None,
        )
        options = (
            visible_shields()
            if visible_shields is not None
            else list(owner.shield_zone.cards)
        )
        if not options:
            return None

        return self.game.target_selector.select(
            self.player,
            options,
            prompt="Choose shield slot to stack on",
        )

    def _requires_shield_stack(
        self,
        to_zone,
    ):
        if to_zone != ZoneType.SHIELD:
            return False

        if (
            self.spec.get(
                "shield_stack_on",
                self.spec.get("stack_on"),
            )
            is not None
        ):
            return True

        return self.spec.get(
            "shield_placement",
            self.spec.get("shield_destination", "new"),
        ) in (
            "choose_slot",
            "stack",
            "stack_on_slot",
        )


class V2IfEffect(BaseEffect):
    """Resolve one of two effect lists based on a structured condition."""

    def __init__(
        self,
        spec,
        factory,
        player,
        source_card,
    ):
        super().__init__()
        self.spec = spec
        self.factory = factory
        self.player = player
        self.source_card = source_card

    def resolve(
        self,
    ):
        matched = self._condition_matches()
        effects = self.factory.build_many(
            self.spec.get("then" if matched else "else", []),
            self.player,
            source_card=self.source_card,
        )
        self._resolve_effects(effects)
        return bool(effects)

    def can_attempt(
        self,
    ):
        matched = self._condition_matches()
        branch_key = "then" if matched else "else"
        return bool(
            self.spec.get(
                branch_key,
                [],
            )
        )

    def _condition_matches(
        self,
    ):
        effect_context = EffectContext.from_package_context(
            self.package_context
        )
        evaluator = ConditionEvaluator(
            self.factory.game
        )
        return evaluator.evaluate(
            self.spec.get("condition"),
            {
                "game": self.factory.game,
                "player": self.player,
                "controller": self.player,
                "source_card": self.source_card,
                "source_info": self.source_info,
                "event": self.package_context.get("event"),
                "package_context": self.package_context,
                "effect_context": effect_context,
            },
        )

    def _resolve_effects(
        self,
        effects,
    ):
        previous_attempted = True
        for effect in effects:
            effect.package_context = self.package_context
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            connector = getattr(effect, "package_connector", "after")

            if connector == "then" and previous_attempted is not True:
                previous_attempted = None
                continue

            if (
                connector in ("otherwise", "else")
                and previous_attempted is not False
            ):
                previous_attempted = None
                continue

            attempted = self._can_attempt(effect)
            if attempted:
                result = effect.resolve()
                if isinstance(result, bool):
                    attempted = result

            previous_attempted = attempted

    def _can_attempt(
        self,
        effect,
    ):
        can_attempt = getattr(
            effect,
            "can_attempt",
            None,
        )
        if can_attempt is None:
            return True

        return can_attempt()


class V2ChoiceEffect(V2IfEffect):
    """Let the player choose one effect branch.

    ``selector`` / ``choosing_player`` で選択するプレイヤーを指定できる
    （例: ``"opponent"`` で「相手は〜を選ぶ」）。分岐内の効果は従来どおり
    能力のコントローラーを基準に解決される。
    """

    def can_attempt(
        self,
    ):
        # V2IfEffect.can_attempt は then/else 分岐を見るが、選択効果は choices を
        # 持つ。choices があれば試行可能（少なくとも 1 つの分岐を選べる）。
        return bool(
            _as_list(self.spec.get("choices"))
        )

    def resolve(
        self,
    ):
        choices = _as_list(
            self.spec.get("choices")
        )
        if not choices:
            return False

        selected_index = self.factory.game.choice_manager.select(
            self._chooser(),
            [
                self._choice_option(index, choice)
                for index, choice in enumerate(choices)
            ],
            prompt=self.spec.get("prompt", "Choose an effect"),
        )
        if selected_index is None:
            return False

        choice = choices[int(selected_index)]
        effects = self.factory.build_many(
            choice.get("effects", []),
            self.player,
            source_card=self.source_card,
        )
        self._resolve_effects(effects)
        return bool(effects)

    def _choice_option(
        self,
        index,
        choice,
    ):
        if not isinstance(choice, dict):
            return ChoiceOption(index)

        return ChoiceOption(
            index,
            choice_id=choice.get(
                "choice_id",
                choice.get("id"),
            ),
            label=choice.get(
                "label",
                f"choice {index + 1}",
            ),
        )

    def _chooser(
        self,
    ):
        args = EffectArgumentResolver(
            self.factory.game
        )
        context = args.context(
            self.player,
            source_card=self.source_card,
            source_info=self.source_info,
            package_context=self.package_context,
        )
        return args.player(
            self.spec.get(
                "selector",
                self.spec.get("choosing_player", "self"),
            ),
            context,
        )


class V2ChooseNumberEffect(BaseEffect):
    """Choose a number and store it under ``store_as``."""

    def __init__(
        self,
        spec,
        game,
        player,
    ):
        super().__init__()
        self.spec = spec
        self.game = game
        self.player = player

    def resolve(
        self,
    ):
        minimum = int(self.spec.get("min", 0))
        maximum = int(self.spec.get("max"))
        selected = self.game.choice_manager.select(
            self.player,
            list(range(minimum, maximum + 1)),
            prompt=self.spec.get("prompt", "Choose a number"),
        )
        if selected is None:
            return False

        store_as = self.spec.get("store_as")
        if store_as:
            EffectContext.from_package_context(
                self.package_context
            ).store(
                store_as,
                int(selected),
            )

        return True


class V2AlternativeEffect(V2IfEffect):
    """Resolve an alternative branch when its condition is satisfied."""

    def resolve(
        self,
    ):
        effect_context = EffectContext.from_package_context(
            self.package_context
        )
        evaluator = ConditionEvaluator(
            self.factory.game
        )
        can_use_alternative = evaluator.evaluate(
            self.spec.get(
                "condition",
                {
                    "type": "always",
                },
            ),
            {
                "game": self.factory.game,
                "player": self.player,
                "controller": self.player,
                "source_card": self.source_card,
                "source_info": self.source_info,
                "event": self.package_context.get("event"),
                "package_context": self.package_context,
                "effect_context": effect_context,
            },
        )
        key = "alternative" if can_use_alternative else "default"
        effects = self.factory.build_many(
            self.spec.get(
                key,
                self.spec.get(
                    f"{key}_effects",
                    [],
                ),
            ),
            self.player,
            source_card=self.source_card,
        )
        self._resolve_effects(effects)
        return bool(effects)


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return value

    return [value]


def _ignore_cost(
    spec,
):
    if "without_cost" in spec:
        return bool(spec["without_cost"])

    if "ignore_cost" in spec:
        return bool(spec["ignore_cost"])

    if "pay_cost" in spec:
        return not bool(spec["pay_cost"])

    cost_mode = spec.get("cost_mode")
    if cost_mode in (
        "free",
        "ignore",
        "without_cost",
    ):
        return True

    if cost_mode in (
        "pay",
        "pay_cost",
        "normal",
    ):
        return False

    return True


def _duration_key(
    value,
):
    if value is None:
        return None

    if isinstance(value, dict):
        value = value.get(
            "type",
            value.get("duration", value.get("until")),
        )

    return str(value).lower()
