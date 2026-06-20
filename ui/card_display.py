"""
CLI/debug output helpers for card names and board rows.
"""

from cards.card import Civilization
from core.battle_display_labels import (
    battle_display_label,
    ensure_battle_display_label,
)
from core.pending_cards import visible_cards
from core.seal_utils import is_seal_card


_CIVILIZATION_NAMES = (
    (Civilization.FIRE, "Fire"),
    (Civilization.WATER, "Water"),
    (Civilization.NATURE, "Nature"),
    (Civilization.LIGHT, "Light"),
    (Civilization.DARKNESS, "Darkness"),
)

EVOLUTION_SOURCE_SEPARATOR = " > "


def civilization_label(card):
    civilizations = _card_civilizations(card)
    names = [
        name
        for bit, name in _CIVILIZATION_NAMES
        if civilizations & bit
    ]
    return "/".join(names) if names else "None"


def tap_state_label(card):
    return (
        "TAP"
        if getattr(
            card,
            "tapped",
            False,
        )
        else "UNTAP"
    )


def format_mana_zone_heading(
    player,
    prefix="Mana Zone",
):
    return (
        f"{prefix} "
        f"(Total: {_mana_total(player)} | "
        f"Available: {_available_mana(player)})"
    )


def format_card_name(
    card,
    active_face=None,
    mark_evolution=True,
    mark_battle_label=True,
):
    if is_seal_card(card):
        # 封印カードは裏向きでカード種が見えないため、
        # 元カード名に基づくアルファベット識別子は付けない。
        # かわりにどのクリーチャーを封印しているかを示す。
        name = "Seal (face down)"
        target_label = _sealed_target_label(card)
        if target_label:
            name = f"{name} -> on {target_label}"
        return name

    if getattr(card, "zone", None).__class__.__name__ == "ZoneType":
        if card.zone.name == "SHIELD":
            return format_shield_card_name(card)

    name = _format_twinpact_name(
        card,
        active_face,
    )

    if (
        mark_evolution
        and getattr(card, "is_evolution", False)
        and not getattr(card, "is_evolution_source", False)
    ):
        name = f"*{name}"

    if mark_battle_label:
        ensure_battle_display_label(card)
        label = battle_display_label(card)
        if label:
            name = f"{name} {label}"

    seal_count = len(
        getattr(card, "seals", ()) or ()
    )
    if seal_count:
        name = f"{name} [SEALED x{seal_count}]"

    return name


def _sealed_target_label(seal_card):
    target = getattr(
        seal_card,
        "sealed_target",
        None,
    )
    if target is None:
        return ""

    name = _format_twinpact_name(target)
    label = battle_display_label(target)
    if label:
        name = f"{name} {label}"
    return name


def ordered_battle_zone_cards(player):
    """バトルゾーンのカードを、封印カードがその封印先クリーチャーの
    直下に並ぶ順序で返す。

    各要素は ``(card, is_attached_seal)`` のタプル。封印先が
    バトルゾーンに見当たらない封印カード（孤立封印）はトップレベル
    要素として残す。
    """
    cards = list(
        visible_cards(player.battle_zone.cards)
    )
    card_ids = {id(card) for card in cards}

    seals_by_target = {}
    attached = set()
    for card in cards:
        if not is_seal_card(card):
            continue
        target = getattr(
            card,
            "sealed_target",
            None,
        )
        if target is not None and id(target) in card_ids:
            seals_by_target.setdefault(
                id(target),
                [],
            ).append(card)
            attached.add(id(card))

    ordered = []
    for card in cards:
        if id(card) in attached:
            continue
        ordered.append((card, False))
        for seal in seals_by_target.get(id(card), ()):
            ordered.append((seal, True))

    return ordered


def format_shield_card_name(
    card,
):
    owner = getattr(
        card,
        "owner",
        None,
    )
    index = None
    stack_size = 1
    if owner is not None and card in owner.shield_zone.cards:
        slot_index = getattr(
            owner.shield_zone,
            "slot_index",
            None,
        )
        slot_size = getattr(
            owner.shield_zone,
            "slot_size",
            None,
        )
        if slot_index is not None:
            raw_index = slot_index(card)
            if raw_index is not None:
                index = raw_index + 1
        else:
            index = owner.shield_zone.cards.index(card) + 1

        if slot_size is not None:
            stack_size = max(
                1,
                slot_size(card),
            )

    label = (
        f"Shield {index}"
        if index is not None
        else "Shield"
    )
    if stack_size > 1:
        label = f"{label} [{stack_size} cards]"

    if not getattr(
        card,
        "shield_face_up",
        False,
    ):
        return f"{label} (face down)"

    return f"{label}: {_format_twinpact_name(card)} (face up)"


def format_action(choice):
    if choice.__class__.__name__ == "SummonAction":
        name = format_card_name(
            choice.card,
            _creature_face(choice.card),
        )
        from_zone = _action_from_zone_suffix(
            choice.card,
        )
        method_separator = (
            f"{from_zone} "
            if from_zone
            else " "
        )
        if choice.evolution_source is not None:
            return (
                f"Summon {name}{method_separator}"
                f"as NEO evolution "
                f"on {format_card_name(choice.evolution_source)}"
            )
        if getattr(
            choice,
            "alternative_cost",
            None,
        ) is not None:
            return (
                f"Summon {name}{method_separator}"
                "by alternative cost"
            )
        if getattr(choice, "play_method", None) == "g_zero":
            return (
                f"Summon {name}{method_separator}"
                "by G-Zero"
            )
        return f"Summon {name}{from_zone}"

    if choice.__class__.__name__ == "CastSpellAction":
        from_zone = _action_from_zone_suffix(
            choice.spell,
        )
        suffix = (
            " by G-Zero"
            if getattr(choice, "play_method", None) == "g_zero"
            else ""
        )
        return (
            "Cast "
            f"{format_card_name(choice.spell, _spell_face(choice.spell))}"
            f"{from_zone}"
            f"{suffix}"
        )

    if choice.__class__.__name__ == "AttackAction":
        return (
            f"{format_card_name(choice.attacker)} "
            f"attacks {format_card_name(choice.target)}"
        )

    return str(choice)


def format_battle_card(
    card,
    can_attack=False,
    mark_battle_label=True,
):
    if is_seal_card(card):
        return format_card_name(
            card,
            mark_battle_label=mark_battle_label,
        )

    parts = [
        (
            f"[{tap_state_label(card)}] "
            f"{format_card_name(card, mark_battle_label=mark_battle_label)}"
        )
    ]

    current_power = getattr(
        card,
        "get_current_power",
        None,
    )
    if current_power is not None:
        parts.append(
            f"Power: {current_power()}"
        )

    line = " | ".join(parts)

    if can_attack:
        line = f"{line} [Attackable]"

    sources = _evolution_source_names(
        card,
        mark_battle_label=mark_battle_label,
    )
    if sources:
        line = (
            f"{line} "
            f"(source: {EVOLUTION_SOURCE_SEPARATOR.join(sources)})"
        )

    return line


def _card_civilizations(card):
    get_all = getattr(
        card,
        "get_all_civilizations",
        None,
    )
    if callable(get_all):
        return get_all()
    return getattr(
        card,
        "civilizations",
        0,
    )


def _mana_total(player):
    mana_zone = getattr(
        player,
        "mana_zone",
        None,
    )
    if mana_zone is None:
        return 0

    return sum(
        _mana_value(player, card)
        for card in visible_cards(
            mana_zone.cards,
        )
    )


def _available_mana(player):
    available_mana = getattr(
        player,
        "available_mana",
        None,
    )
    if available_mana is not None:
        return available_mana()

    mana_zone = getattr(
        player,
        "mana_zone",
        None,
    )
    if mana_zone is None:
        return 0

    return sum(
        _mana_value(player, card)
        for card in visible_cards(
            mana_zone.cards,
        )
        if not getattr(
            card,
            "tapped",
            False,
        )
    )


def _mana_value(
    player,
    card,
):
    mana_value = getattr(
        player,
        "mana_value",
        None,
    )
    if mana_value is None:
        return 1

    return mana_value(card)


def _format_twinpact_name(
    card,
    active_face=None,
):
    if not _is_twinpact(card):
        return getattr(card, "name", str(card))

    face = active_face or getattr(
        card,
        "selected_face",
        None,
    )
    if face is None:
        return card.name

    parts = card.name.split(" / ")
    return " / ".join(
        f"【{part}】"
        if part == face.name
        else part
        for part in parts
    )


def _creature_face(card):
    if _is_twinpact(card):
        return card.creature_face
    return None


def _spell_face(card):
    if _is_twinpact(card):
        return card.spell_face
    return None


def _is_twinpact(card):
    return bool(getattr(card, "is_twinpact", False))


def _action_from_zone_suffix(card):
    zone = getattr(
        card,
        "zone",
        None,
    )
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
    return (
        " from "
        + labels.get(
            zone_name,
            zone_name.lower(),
        )
    )


def _evolution_source_names(
    card,
    mark_battle_label=True,
):
    names = []

    for source in getattr(
        card,
        "evolution_sources",
        [],
    ):
        names.append(
            format_card_name(
                source,
                mark_evolution=False,
                mark_battle_label=mark_battle_label,
            )
        )
        names.extend(
            _evolution_source_names(
                source,
                mark_battle_label=mark_battle_label,
            )
        )

    return names
