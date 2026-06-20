"""Apply an effect to each card resolved from a generic source."""

from actions.attack_creature_action import AttackCreatureAction
from core.effect_argument_resolver import parse_duration_spec
from effects.base.base_effect import BaseEffect
from effects.combat.tap_effect import TapEffect
from effects.combat.temporary_combat_restriction_effect import (
    TemporaryCombatRestrictionEffect,
)
from effects.combat.untap_effect import UntapEffect
from effects.composition.card_source_resolver import resolve_card_source
from effects.modifiers.add_power_modifier_effect import AddPowerModifierEffect
from effects.modifiers.timed_power_modifier_effect import TimedPowerModifierEffect
from effects.zones.bounce_effect import BounceEffect
from effects.zones.dectroy_effect import DestroyEffect
from effects.zones.seal_effect import AttachSealEffect
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class ForEachEffect(BaseEffect):
    """Resolve ``effect_spec`` once for each card in a source collection."""

    def __init__(
        self,
        game,
        player,
        source,
        effect_spec,
        store_key=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.source = source
        self.store_key = store_key
        self.effect_spec = effect_spec or {}

    def resolve(self):
        cards = resolve_card_source(
            {
                "source": self.source,
                "store_key": self.store_key,
            },
            self.game,
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )
        if not cards:
            return False

        attempted = False
        for card in cards:
            attempted = self._resolve_on(card) or attempted

        return attempted

    def _resolve_on(self, target):
        effect_id = (
            self.effect_spec.get("effect_id")
            or self.effect_spec.get("id")
        )

        if effect_id == "destroy":
            DestroyEffect(target=target, game=self.game).resolve()
            return True

        if effect_id == "tap":
            return TapEffect(target=target, game=self.game).resolve()

        if effect_id == "untap":
            return UntapEffect(
                target=target,
                game=self.game,
                player=self.player,
            ).resolve()

        if effect_id == "bounce":
            BounceEffect(target=target, game=self.game).resolve()
            return True

        if effect_id == "temporary_combat_restriction":
            effect = TemporaryCombatRestrictionEffect(
                game=self.game,
                source_card=self.source_card,
                target_card=target,
                restrictions=self.effect_spec.get(
                    "restrictions",
                    [],
                ),
                duration_type=parse_duration_spec(
                    self.effect_spec.get("duration")
                ),
            )
            effect.package_context = self.package_context
            effect.resolve()
            return True

        if effect_id == "modify_power":
            self._resolve_modify_power(target)
            return True

        if effect_id == "attach_seal":
            effect = AttachSealEffect(
                player=self.player,
                game=self.game,
                target=target,
                amount=self.effect_spec.get(
                    "amount",
                    self.effect_spec.get("count", 1),
                ),
                seal_player=self.effect_spec.get("seal_player"),
            )
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.package_context = self.package_context
            effect.resolve()
            return True

        if effect_id == "battle":
            source = self._battle_source()
            if source is None:
                return False
            self.game.combat_manager.process_battle(
                AttackCreatureAction(
                    source.owner,
                    source,
                    target,
                )
            )
            return True

        if effect_id == "move_card":
            return self._move_target(target)

        return self._resolve_nested_effect(target)

    def _resolve_modify_power(
        self,
        target,
    ):
        amount = self.effect_spec.get(
            "amount",
            self.effect_spec.get("value", 0),
        )
        duration = self.effect_spec.get("duration")
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
        if target is self.source_card:
            effect.trigger_snapshot = self.trigger_snapshot
        effect.package_context = self.package_context
        effect.resolve()

    def _battle_source(self):
        target = self.effect_spec.get("target")
        if target == "self":
            return self.source_card

        if isinstance(target, dict):
            from core.effect_argument_resolver import EffectArgumentResolver

            args = EffectArgumentResolver(self.game)
            context = args.context(
                self.player,
                source_card=self.source_card,
                package_context=self.package_context,
            )
            cards = args.cards(target, context)
            return cards[0] if cards else None

        return target

    def _move_target(
        self,
        target,
    ):
        from_zone = parse_zone(
            self.effect_spec.get("from_zone", "battle")
        )
        to_zone = parse_zone(
            self.effect_spec.get("to_zone", "shield")
        )

        kwargs = {}
        if to_zone == ZoneType.SHIELD:
            shield_stack_on = self._shield_stack_on(
                target.owner,
            )
            if (
                self._requires_shield_stack()
                and shield_stack_on is None
            ):
                return False
            kwargs["shield_face_up"] = self._shield_face_up()
            kwargs["shield_stack_on"] = shield_stack_on

        moved = self.game.card_mover.move(
            card=target,
            owner=target.owner,
            from_zone=from_zone,
            to_zone=to_zone,
            reason=self.effect_spec.get(
                "reason",
                "move_card",
            ),
            **kwargs,
        )
        if moved and self.effect_spec.get("destination_position") == "top":
            destination = target.owner.get_zone(to_zone)
            if target in destination.cards:
                destination.cards.remove(target)
                destination.cards.insert(0, target)

        if moved and "tapped" in self.effect_spec:
            target.tapped = bool(self.effect_spec["tapped"])

        return moved

    def _resolve_nested_effect(
        self,
        target,
    ):
        from effects.registry import build_effects

        spec = {
            **self.effect_spec,
            "target": self.effect_spec.get("target", target),
            "card": self.effect_spec.get("card", target),
            "cards": self.effect_spec.get("cards", [target]),
        }
        effects = build_effects(
            [spec],
            self.game,
            self.player,
            source_card=self.source_card,
        )
        attempted = False
        for effect in effects:
            effect.package_context = self.package_context
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.trigger_snapshot = self.trigger_snapshot
            result = effect.resolve()
            attempted = attempted or result is not False

        return attempted

    def _shield_face_up(self):
        to_zone = self.effect_spec.get("to_zone")
        if to_zone not in (
            "shield",
            "shield_zone",
        ):
            return None

        face_options = self.effect_spec.get(
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
    ):
        if not self._requires_shield_stack():
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

    def _requires_shield_stack(self):
        return self.effect_spec.get(
            "shield_placement",
            self.effect_spec.get("shield_destination", "new"),
        ) in (
            "choose_slot",
            "stack",
            "stack_on_slot",
        )


class ForEachStoredEffect(ForEachEffect):
    """Backward-compatible wrapper for ``for_each_stored`` specs."""

    def __init__(
        self,
        game,
        player,
        source,
        effect_spec,
    ):
        super().__init__(
            game=game,
            player=player,
            source=source,
            effect_spec=effect_spec,
        )
