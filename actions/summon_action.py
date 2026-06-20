"""
手札からクリーチャーを召喚するアクションのデータを保持するクラス。
"""

from actions.base_action import BaseAction
from actions.play_method import (
    PlayMethod,
    ignores_mana_cost,
    normalize_play_method,
)
from ui.card_display import format_card_name


class SummonAction(BaseAction):

    def __init__(
        self,
        player,
        card,
        ignore_cost=False,
        evolution_source=None,
        alternative_cost=None,
        play_method=None,
        cost_mode=None,
        play_permission=None,
        play_permissions=None,
        g_zero_ability=None,
    ):
        super().__init__(player)

        self.player = player
        self.card = card
        self.evolution_source = evolution_source
        self.alternative_cost = alternative_cost
        self.play_method = normalize_play_method(
            play_method
            if play_method is not None
            else cost_mode,
            ignore_cost=ignore_cost,
            alternative_cost=alternative_cost,
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
        from_zone = _from_zone_suffix(self.card)
        method_separator = (
            f"{from_zone} "
            if from_zone
            else " "
        )

        if self.evolution_source is not None:
            return (
                f"Summon "
                f"{format_card_name(self.card)}"
                f"{method_separator}"
                f"as NEO evolution "
                f"on {format_card_name(self.evolution_source)}"
            )

        if self.alternative_cost is not None:
            return (
                f"Summon "
                f"{format_card_name(self.card)}"
                f"{method_separator}"
                f"by alternative cost"
            )

        if self.play_method == PlayMethod.G_ZERO:
            return (
                f"Summon "
                f"{format_card_name(self.card)}"
                f"{method_separator}"
                f"by G-Zero"
            )

        return (
            f"Summon "
            f"{format_card_name(self.card)}"
            f"{from_zone}"
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
        "GRAVEYARD": "graveyard",
        "MANA": "mana",
        "DECK": "deck",
        "SHIELD": "shield",
        "BATTLE": "battle zone",
    }
    label = labels.get(
        zone_name,
        zone_name.lower(),
    )
    return f" from {label}"
