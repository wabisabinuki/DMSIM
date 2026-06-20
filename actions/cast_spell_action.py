"""
手札から呪文を唱える（キャストする）アクションのデータを保持するクラス。
"""

from ui.card_display import format_card_name
from actions.play_method import (
    PlayMethod,
    ignores_mana_cost,
    normalize_play_method,
)

class CastSpellAction:

    def __init__(
        self,
        player,
        spell,
        ignore_cost=False,
        play_method=None,
        cost_mode=None,
        play_permission=None,
        play_permissions=None,
        g_zero_ability=None,
    ):

        self.player = player
        self.spell = spell
        self.play_method = normalize_play_method(
            play_method
            if play_method is not None
            else cost_mode,
            ignore_cost=ignore_cost,
        )
        self.cost_mode = self.play_method
        self.ignore_cost = (
            bool(ignore_cost)
            or ignores_mana_cost(self.play_method)
        )
        self.play_permission = play_permission
        self.play_permissions = _normalize_play_permissions(
            play_permission,
            play_permissions,
        )
        self.selected_play_permission = None
        self.g_zero_ability = g_zero_ability

    def __str__(self):

        from_zone = _from_zone_suffix(self.spell)
        suffix = (
            " by G-Zero"
            if self.play_method == PlayMethod.G_ZERO
            else ""
        )
        return (
            f"Cast "
            f"{format_card_name(self.spell)}"
            f"{from_zone}"
            f"{suffix}"
        )


def _normalize_play_permissions(
    play_permission,
    play_permissions,
):
    permissions = []
    seen = set()

    def add(permission):
        if permission is None:
            return

        key = id(permission)
        if key in seen:
            return

        seen.add(key)
        permissions.append(permission)

    add(play_permission)

    if play_permissions is not None:
        for permission in play_permissions:
            add(permission)

    return permissions


def _from_zone_suffix(card):
    zone = getattr(
        card,
        "zone",
        None,
    )
    if zone is None:
        return ""

    zone_name = getattr(
        zone,
        "name",
        "",
    )
    if zone_name in (
        "",
        "HAND",
    ):
        return ""

    labels = {
        "GRAVEYARD": " from graveyard",
        "MANA": " from mana",
        "DECK": " from deck",
        "SHIELD": " from shield",
    }
    return labels.get(
        zone_name,
        f" from {zone_name.lower()}",
    )
