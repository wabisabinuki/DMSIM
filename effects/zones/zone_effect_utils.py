"""Shared helpers for JSON-authored zone effects."""

from zones.zone_type import ZoneType


ZONE_ALIASES = {
    "battle": ZoneType.BATTLE,
    "battle_zone": ZoneType.BATTLE,
    "deck": ZoneType.DECK,
    "grave": ZoneType.GRAVEYARD,
    "graveyard": ZoneType.GRAVEYARD,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "mana_zone": ZoneType.MANA,
    "shield": ZoneType.SHIELD,
    "shields": ZoneType.SHIELD,
    "shield_zone": ZoneType.SHIELD,
    "super_dimension": ZoneType.SUPER_DIMENSION,
    "super_dimension_zone": ZoneType.SUPER_DIMENSION,
    "hyperspatial": ZoneType.SUPER_DIMENSION,
}


def parse_zone(
    value,
):
    if isinstance(
        value,
        ZoneType,
    ):
        return value

    key = str(value).lower()
    if key not in ZONE_ALIASES:
        raise ValueError(f"Unknown zone: {value}")

    return ZONE_ALIASES[key]


def resolve_player(
    game,
    controller,
    value=None,
):
    key = (
        "self"
        if value is None
        else str(value).lower()
    )

    if key in (
        "self",
        "controller",
        "own",
        "owner",
    ):
        return controller

    if key == "opponent":
        return game.query.get_opponent(controller)

    raise ValueError(f"Unknown target player: {value}")


def default_selection_for_zone(
    zone_type,
):
    if zone_type == ZoneType.DECK:
        return "top"

    return "choose"


def merge_filter_spec(
    base=None,
    extra=None,
):
    result = dict(base or {})
    result.update(extra or {})
    return result
