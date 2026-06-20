"""Resolve v2 ability target specs and store selected values."""

from dataclasses import dataclass

from core.card_filter_evaluator import CardFilterEvaluator
from core.pending_cards import visible_cards
from core.ref_resolver import RefResolver
from effects.effect_context import EffectContext
from effects.zones.zone_effect_utils import parse_zone


@dataclass
class TargetResolution:
    success: bool
    values: dict


class TargetResolver:
    """Resolve target declarations before effect specs consume refs."""

    def __init__(
        self,
        game,
    ):
        self.game = game
        self.refs = RefResolver(game)
        self.card_filters = CardFilterEvaluator(game)

    def resolve(
        self,
        target_specs,
        context=None,
    ):
        context = context or {}
        package_context = context.setdefault(
            "package_context",
            {},
        )
        effect_context = context.get("effect_context")
        if effect_context is None:
            effect_context = EffectContext.from_package_context(
                package_context
            )
            context["effect_context"] = effect_context

        values = {}
        for spec in _as_list(target_specs):
            selected = self._resolve_one(
                spec,
                context,
            )
            if selected is _FAILED:
                return TargetResolution(
                    success=False,
                    values=values,
                )

            target_id = spec["id"]
            values[target_id] = selected
            package_context[target_id] = selected
            effect_context.store(
                target_id,
                selected,
            )

        return TargetResolution(
            success=True,
            values=values,
        )

    def candidates(
        self,
        target_spec,
        context=None,
    ):
        context = context or {}
        return [
            card
            for card in self._source_cards(
                target_spec,
                context,
            )
            if self.card_filters.matches(
                card,
                target_spec.get("filter", {}),
                self._filter_context(context),
            )
        ]

    def _resolve_one(
        self,
        spec,
        context,
    ):
        if not isinstance(spec, dict):
            raise ValueError(
                f"target must be an object: {spec!r}"
            )

        if not isinstance(spec.get("id"), str):
            raise ValueError(
                f"target requires string id: {spec!r}"
            )

        options = self.candidates(
            spec,
            context,
        )
        minimum = int(spec.get("min", 1))
        maximum = int(spec.get("max", 1))
        optional = bool(spec.get("optional", False))

        if not options and minimum > 0 and not optional:
            return _FAILED

        chooser = self._chooser(
            spec,
            context,
        )
        prompt = spec.get(
            "prompt",
            "Choose a target",
        )

        if maximum <= 1:
            selected = self.game.target_selector.select(
                chooser,
                options,
                prompt=prompt,
                can_skip=optional or minimum == 0,
            )
            if selected is None and minimum > 0 and not optional:
                return _FAILED
            return selected

        selected = self.game.target_selector.select_multiple(
            chooser,
            options,
            prompt=prompt,
            min_count=0 if optional else minimum,
            max_count=maximum,
            can_skip=optional,
        )
        if len(selected) < minimum and not optional:
            return _FAILED

        return selected

    def _source_cards(
        self,
        spec,
        context,
    ):
        source = spec.get("from")
        if not isinstance(source, dict):
            raise ValueError(
                f"target.from must be an object: {source!r}"
            )

        player = self._player(
            source.get("player", "controller"),
            context,
        )
        zone = parse_zone(
            source.get("zone")
        )
        if player is None:
            return []

        player_zone = player.get_zone(zone)
        visible_shields = getattr(
            player_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return visible_cards(
            player_zone.cards
        )

    def _chooser(
        self,
        spec,
        context,
    ):
        return self._player(
            spec.get("chooser", "controller"),
            context,
        )

    def _player(
        self,
        value,
        context,
    ):
        ref = PLAYER_REF_ALIASES.get(value)
        if ref is not None:
            return self.refs.resolve_ref(
                ref,
                context,
            )

        if isinstance(value, dict) and set(value) == {"ref"}:
            return self.refs.resolve(
                value,
                context,
            )

        return value

    def _filter_context(
        self,
        context,
    ):
        controller = self.refs.resolve_ref(
            "controller",
            context,
        )
        return {
            **context,
            "controller": controller,
            "player": controller,
        }


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


_FAILED = object()

PLAYER_REF_ALIASES = {
    "controller": "controller",
    "self": "controller",
    "owner": "controller",
    "opponent": "opponent",
}
