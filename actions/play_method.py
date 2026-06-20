"""Shared play method labels for card-use actions."""


class PlayMethod:
    NORMAL_COST = "normal_cost"
    ALTERNATIVE_COST = "alternative_cost"
    WITHOUT_COST = "without_cost"
    G_ZERO = "g_zero"


_ALIASES = {
    None: None,
    "normal": PlayMethod.NORMAL_COST,
    "normal_cost": PlayMethod.NORMAL_COST,
    "NORMAL_COST": PlayMethod.NORMAL_COST,
    "alternative": PlayMethod.ALTERNATIVE_COST,
    "alternative_cost": PlayMethod.ALTERNATIVE_COST,
    "ALTERNATIVE_COST": PlayMethod.ALTERNATIVE_COST,
    "free": PlayMethod.WITHOUT_COST,
    "ignore": PlayMethod.WITHOUT_COST,
    "without_cost": PlayMethod.WITHOUT_COST,
    "WITHOUT_COST": PlayMethod.WITHOUT_COST,
    "g_zero": PlayMethod.G_ZERO,
    "G_ZERO": PlayMethod.G_ZERO,
    "g-zero": PlayMethod.G_ZERO,
    "G-Zero": PlayMethod.G_ZERO,
}

_COST_IGNORED = frozenset(
    (
        PlayMethod.WITHOUT_COST,
        PlayMethod.G_ZERO,
    )
)


def normalize_play_method(
    play_method=None,
    ignore_cost=False,
    alternative_cost=None,
):
    normalized = _ALIASES.get(
        play_method,
        play_method,
    )

    if normalized is not None:
        return normalized

    if ignore_cost:
        return PlayMethod.WITHOUT_COST

    if alternative_cost is not None:
        return PlayMethod.ALTERNATIVE_COST

    return PlayMethod.NORMAL_COST


def ignores_mana_cost(
    play_method,
):
    return normalize_play_method(play_method) in _COST_IGNORED


def is_g_zero(
    play_method,
):
    return normalize_play_method(play_method) == PlayMethod.G_ZERO
