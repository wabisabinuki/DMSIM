"""
条件に合う対象を選び、選んだ対象へ単発効果（または効果のリスト）を適用する汎用効果。
"""

from effects.base.base_effect import BaseEffect
from actions.attack_creature_action import AttackCreatureAction
from effects.combat.tap_effect import TapEffect
from effects.combat.untap_effect import UntapEffect
from effects.combat.temporary_combat_restriction_effect import (
    TemporaryCombatRestrictionEffect,
)
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.effect_argument_resolver import (
    EffectArgumentResolver,
    parse_duration_spec,
)
from effects.modifiers.add_power_modifier_effect import AddPowerModifierEffect
from effects.modifiers.timed_power_modifier_effect import (
    TimedPowerModifierEffect,
)
from effects.zones.bounce_effect import BounceEffect
from effects.zones.dectroy_effect import DestroyEffect
from effects.zones.seal_effect import AttachSealEffect
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class SelectThenEffect(BaseEffect):

    def __init__(
        self,
        player,
        game,
        candidates,
        filter_spec,
        effect_spec,
        prompt,
        optional=True,
        store_as=None,
    ):
        super().__init__()

        self.player = player
        self.game = game
        self.candidates = candidates
        self.filter_spec = filter_spec
        # 1つの dict か、同じ対象へ順番に適用する dict のリストを受け付ける。
        self.effect_specs = (
            list(effect_spec)
            if isinstance(effect_spec, list)
            else [effect_spec]
        )
        self.prompt = prompt
        self.optional = optional
        self.store_as = store_as

    def resolve(self):
        options = self._options()

        if not options:
            return False

        target = self.game.target_selector.select(
            self.player,
            options,
            prompt=self.prompt,
            can_skip=self.optional,
        )

        if target is None:
            return False

        if self.store_as:
            self.package_context[self.store_as] = target

        for effect_spec in self.effect_specs:
            self._resolve_effect(
                target,
                effect_spec,
            )
        return True

    def can_attempt(self):
        return bool(self._options())

    def _options(self):
        options = [
            card
            for card in self._candidates()
            if matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.filter_spec,
                context=self._filter_context(),
            )
        ]

        return options

    def _filter_context(
        self,
    ):
        return {
            **self.package_context,
            "player": self.player,
            "source_card": self.source_card,
        }

    def _candidates(
        self,
    ):
        if self.candidates == "creatures":
            return self.game.query.get_selectable_creatures(
                source=self.source_card or self.player,
            )

        if self.candidates == "opponent_creatures":
            opponent = self.game.query.get_opponent(
                self.player
            )
            return self.game.query.get_selectable_creatures(
                source=self.source_card or self.player,
                controller=opponent,
            )

        if self.candidates == "own_creatures":
            return self.game.query.get_selectable_creatures(
                source=self.source_card or self.player,
                controller=self.player,
            )

        if self.candidates == "own_other_creatures":
            return [
                creature
                for creature in self.game.query.get_selectable_creatures(
                    source=self.source_card or self.player,
                    controller=self.player,
                )
                if creature is not self.source_card
            ]

        if self.candidates == "opponent_battle_zone":
            opponent = self.game.query.get_opponent(
                self.player
            )
            return self.game.query.get_battle_cards(
                controller=opponent,
            )

        if self.candidates == "own_battle_zone":
            return self.game.query.get_battle_cards(
                controller=self.player,
            )

        if self.candidates in ("battle", "battle_zone", "all_battle_zone"):
            return self.game.query.get_battle_cards()

        raise ValueError(f"Unknown candidates: {self.candidates}")

    def _resolve_effect(
        self,
        target,
        effect_spec,
    ):
        effect_id = effect_spec.get("effect_id")
        if effect_id is None:
            effect_id = effect_spec["id"]

        if effect_id == "bounce":
            BounceEffect(
                target=target,
                game=self.game,
            ).resolve()
            return

        if effect_id == "destroy":
            DestroyEffect(
                target=target,
                game=self.game,
            ).resolve()
            return

        if effect_id == "tap":
            TapEffect(
                target=target,
                game=self.game,
            ).resolve()
            return

        if effect_id == "untap":
            UntapEffect(
                target=target,
                game=self.game,
                player=self.player,
            ).resolve()
            return

        if effect_id == "temporary_combat_restriction":
            restriction = TemporaryCombatRestrictionEffect(
                game=self.game,
                source_card=self.source_card,
                target_card=target,
                restrictions=effect_spec.get(
                    "restrictions",
                    [],
                ),
                duration_type=parse_duration_spec(
                    effect_spec.get("duration")
                ),
            )
            restriction.package_context = self.package_context
            restriction.resolve()
            return

        if effect_id == "modify_power":
            self._resolve_modify_power(
                target,
                effect_spec,
            )
            return

        if effect_id == "attach_seal":
            effect = AttachSealEffect(
                player=self.player,
                game=self.game,
                target=target,
                amount=effect_spec.get(
                    "amount",
                    effect_spec.get("count", 1),
                ),
                seal_player=effect_spec.get("seal_player"),
            )
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.package_context = self.package_context
            effect.resolve()
            return

        if effect_id == "battle":
            source = self._battle_source(effect_spec)
            if source is not None:
                self.game.combat_manager.process_battle(
                    AttackCreatureAction(
                        source.owner,
                        source,
                        target,
                    )
                )
            return

        if effect_id == "move_card":
            from_zone = parse_zone(
                effect_spec.get("from_zone", "battle")
            )
            to_zone = parse_zone(
                effect_spec.get("to_zone", "shield")
            )

            if to_zone == ZoneType.SHIELD:
                shield_stack_on = self._shield_stack_on(
                    target.owner,
                    effect_spec,
                )
                if (
                    self._requires_shield_stack(effect_spec)
                    and shield_stack_on is None
                ):
                    return

                self.game.card_mover.move(
                    card=target,
                    owner=target.owner,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    reason=effect_spec.get(
                        "reason",
                        "move_card",
                    ),
                    shield_face_up=self._shield_face_up(effect_spec),
                    shield_stack_on=shield_stack_on,
                )
                return

            self.game.card_mover.move(
                card=target,
                owner=target.owner,
                from_zone=from_zone,
                to_zone=to_zone,
                reason=effect_spec.get(
                    "reason",
                    "move_card",
                ),
            )
            return

        raise ValueError(f"Unknown selected target effect: {effect_id}")

    def _resolve_modify_power(
        self,
        target,
        effect_spec,
    ):
        amount = effect_spec.get(
            "amount",
            effect_spec.get("value", 0),
        )
        duration = effect_spec.get("duration")
        if duration is None:
            AddPowerModifierEffect(
                target=target,
                amount=amount,
            ).resolve()
            return

        effect = TimedPowerModifierEffect(
            source_card=self.source_card,
            target_card=target,
            modifier_amount=amount,
            duration_type=parse_duration_spec(duration),
            game=self.game,
        )
        # trigger_snapshot は発生源の同一性を記録したもの。効果側は
        # target_card の在場チェックに使うため、いま選んだ対象が発生源と
        # 別カードの場合に引き継ぐと必ず不一致になり修正が適用されない。
        if target is self.source_card:
            effect.trigger_snapshot = self.trigger_snapshot
        effect.package_context = self.package_context
        effect.resolve()

    def _battle_source(
        self,
        effect_spec,
    ):
        target = effect_spec.get("target")
        if target == "self":
            return self.source_card

        if isinstance(target, dict):
            args = EffectArgumentResolver(self.game)
            context = args.context(
                self.player,
                source_card=self.source_card,
                package_context=self.package_context,
            )
            cards = args.cards(target, context)
            return cards[0] if cards else None

        return target

    def _shield_face_up(
        self,
        effect_spec,
    ):
        to_zone = effect_spec.get("to_zone")
        if to_zone not in (
            "shield",
            "shield_zone",
        ):
            return None

        face_options = effect_spec.get(
            "face_options",
            ["face_down"],
        )
        if len(face_options) == 1:
            return face_options[0] == "face_up"

        face = self.game.choice_manager.select(
            self.player,
            list(face_options),
            prompt="Choose shield face",
        )
        return face == "face_up"

    def _shield_stack_on(
        self,
        owner,
        effect_spec,
    ):
        if not self._requires_shield_stack(effect_spec):
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
        effect_spec,
    ):
        return effect_spec.get(
            "shield_placement",
            effect_spec.get("shield_destination", "new"),
        ) in (
            "choose_slot",
            "stack",
            "stack_on_slot",
        )
