"""Shared value resolution for v2 effect and replacement specs."""

from core.duration_type import DurationType
from core.ref_resolver import RefResolver
from effects.effect_context import EffectContext
from effects.zones.zone_effect_utils import parse_zone


DURATION_TYPES = {
    "until_start_of_controller_turn": (
        DurationType.UNTIL_START_OF_CONTROLLER_TURN
    ),
    "start_of_controller_turn": (
        DurationType.UNTIL_START_OF_CONTROLLER_TURN
    ),
    "until_end_of_turn": DurationType.UNTIL_END_OF_TURN,
    "end_of_turn": DurationType.UNTIL_END_OF_TURN,
    "until_end_of_opponent_turn": (
        DurationType.UNTIL_END_OF_OPPONENT_TURN
    ),
    "end_of_opponent_turn": (
        DurationType.UNTIL_END_OF_OPPONENT_TURN
    ),
    "permanent": DurationType.PERMANENT,
}

PLAYER_REF_ALIASES = {
    None: "controller",
    "controller": "controller",
    "self": "controller",
    "owner": "controller",
    "opponent": "opponent",
}


class EffectArgumentResolver:
    """Resolve structured effect arguments without implicit string refs."""

    def __init__(
        self,
        game,
    ):
        self.game = game
        self.refs = RefResolver(game)

    def context(
        self,
        player,
        source_card=None,
        source_info=None,
        package_context=None,
        effect_context=None,
        event=None,
    ):
        package_context = package_context or {}
        if event is None:
            event = package_context.get("event")
        effect_context = (
            effect_context
            or EffectContext.from_package_context(
                package_context
            )
        )
        return {
            "game": self.game,
            "player": player,
            "controller": player,
            "source_card": source_card,
            "source_info": source_info,
            "package_context": package_context,
            "effect_context": effect_context,
            "event": event,
        }

    def value(
        self,
        value,
        context,
    ):
        resolved = self.refs.resolve(
            value,
            context,
        )

        if resolved in (
            "self",
            "source",
            "source_card",
        ):
            return context.get("source_card")

        if isinstance(resolved, dict):
            if "card" in resolved:
                return self.value(
                    resolved["card"],
                    context,
                )
            if "target" in resolved:
                return self.value(
                    resolved["target"],
                    context,
                )
            if "cards" in resolved:
                return self.value(
                    resolved["cards"],
                    context,
                )

        return resolved

    def cards(
        self,
        value,
        context,
    ):
        resolved = self.value(
            value,
            context,
        )
        if resolved is None:
            return []

        if isinstance(resolved, list):
            return [
                item
                for item in resolved
                if item is not None
            ]

        return [
            resolved,
        ]

    def player(
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

        resolved = self.value(
            value,
            context,
        )
        return resolved

    def zone(
        self,
        value,
        context,
    ):
        resolved = self.value(
            value,
            context,
        )
        if isinstance(resolved, dict):
            resolved = resolved.get(
                "zone",
                resolved.get("type"),
            )
        return parse_zone(resolved)

    def duration(
        self,
        value,
        context=None,
    ):
        if context is not None:
            value = self.value(
                value,
                context,
            )
        return parse_duration_spec(value)


def parse_duration_spec(
    value,
):
    if isinstance(value, DurationType):
        return value

    if isinstance(value, dict):
        value = value.get(
            "type",
            value.get("duration", value.get("until")),
        )

    key = (
        str(value).lower()
        if value is not None
        else None
    )
    if key in DURATION_TYPES:
        return DURATION_TYPES[key]

    raise ValueError(
        f"Unknown duration type: {value}"
    )
