"""
Temporary display suffixes for cards while they are in the battle zone.
"""

from core.seal_utils import is_seal_card
from zones.zone_type import ZoneType


LABELS = ("A", "B", "C", "D")
_LABEL_ATTR = "_battle_display_label"
_KEY_ATTR = "_battle_display_key"


def ensure_battle_display_label(
    card,
    owner=None,
):
    if is_seal_card(card):
        return None

    if getattr(card, "zone", None) != ZoneType.BATTLE:
        return None

    existing = getattr(
        card,
        _LABEL_ATTR,
        None,
    )
    if existing:
        return existing

    owner = owner or getattr(
        card,
        "owner",
        None,
    )
    if owner is None:
        return None

    key = _label_key(card)
    used = _used_labels(
        owner,
        key,
    )

    for label in LABELS:
        if label not in used:
            setattr(
                card,
                _LABEL_ATTR,
                label,
            )
            setattr(
                card,
                _KEY_ATTR,
                key,
            )
            return label

    return None


def clear_battle_display_label(card):
    for attr in (
        _LABEL_ATTR,
        _KEY_ATTR,
    ):
        if hasattr(card, attr):
            delattr(card, attr)


def battle_display_label(card):
    return getattr(
        card,
        _LABEL_ATTR,
        None,
    )


def _used_labels(
    owner,
    key,
):
    used = set()

    for card in owner.battle_zone.cards:
        _collect_used_labels(
            card,
            key,
            used,
        )

    return used


def _collect_used_labels(
    card,
    key,
    used,
):
    # 封印カードは裏向きでカード名が見えないため、識別子の
    # 名前空間を共有させない（元カード名が残っていても無視する）。
    if is_seal_card(card):
        return

    if (
        getattr(card, _KEY_ATTR, None) == key
        and getattr(card, _LABEL_ATTR, None)
    ):
        used.add(
            getattr(card, _LABEL_ATTR)
        )

    for source in getattr(
        card,
        "evolution_sources",
        [],
    ):
        _collect_used_labels(
            source,
            key,
            used,
        )


def _label_key(card):
    return getattr(
        card,
        "name",
        str(card),
    )
