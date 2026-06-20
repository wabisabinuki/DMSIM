from cards.card import CardType, Civilization
from cards.creature_card import CreatureCard
from cards.spell_card import SpellCard
from cards.twin_pact_card import TwinPactCard
from core.pending_cards import is_card_pending, visible_cards
from core.seal_utils import is_ignored_by_seal, is_seal_card


CIVILIZATION_BITS = {
    "fire": Civilization.FIRE,
    "water": Civilization.WATER,
    "nature": Civilization.NATURE,
    "light": Civilization.LIGHT,
    "darkness": Civilization.DARKNESS,
}

CARD_TYPE_NAMES = {
    "creature": CardType.CREATURE,
    "spell": CardType.SPELL,
    "cross_gear": CardType.CROSS_GEAR,
    "cross gear": CardType.CROSS_GEAR,
    "castle": CardType.CASTLE,
    "weapon": CardType.WEAPON,
    "fortress": CardType.FORTRESS,
    "heartbeat": CardType.HEARTBEAT,
    "field": CardType.FIELD,
    "core": CardType.CORE,
    "aura": CardType.AURA,
    "ceremony": CardType.CEREMONY,
    "artifact": CardType.ARTIFACT,
    "land": CardType.LAND,
    "rule_plus": CardType.RULE_PLUS,
    "rule plus": CardType.RULE_PLUS,
    "tamaseed": CardType.TAMASEED,
    "duelist": CardType.DUELIST,
    "cell": CardType.CELL,
}


def is_creature_card(
    card,
):
    if getattr(
        card,
        "is_evolution_source",
        False,
    ):
        return False

    if is_card_pending(card):
        return False

    if is_ignored_by_seal(card) or is_seal_card(card):
        return False

    if isinstance(
        card,
        CreatureCard,
    ):
        return True

    return (
        isinstance(card, TwinPactCard)
        and card.creature_face is not None
    )


def creature_cost(
    card,
):
    if isinstance(
        card,
        TwinPactCard,
    ):
        return card.creature_face.cost

    return card.cost


def has_civilization(
    card,
    civilization,
    usage_type=None,
):
    bit = CIVILIZATION_BITS[
        str(civilization).lower()
    ]

    return (
        _card_civilizations(
            card,
            usage_type=usage_type,
        )
        & bit
    ) != 0


def matches_card_filter(
    card,
    spec,
    context=None,
    usage_type=None,
):
    if card is None:
        return False

    if is_card_pending(card):
        return False

    if is_ignored_by_seal(card):
        return False

    spec = spec or {}
    inferred_usage_type = usage_type or _usage_type_from_spec(spec)

    if not _matches_exclude_spec(
        card,
        spec,
        context,
    ):
        return False

    if not _matches_type_spec(
        card,
        spec,
        inferred_usage_type,
    ):
        return False

    civilizations = _as_list(
        spec.get(
            "civilizations",
            spec.get("civilization"),
        )
    )
    if civilizations:
        if not any(
            has_civilization(
                card,
                civilization,
                usage_type=inferred_usage_type,
            )
            for civilization in civilizations
        ):
            return False

    mana_civilizations_player = spec.get(
        "civilizations_all_in_mana_zone"
    )
    if mana_civilizations_player is not None:
        player = _resolve_filter_player(
            mana_civilizations_player,
            context,
        )
        if player is None:
            return False
        if not _civilizations_all_in_mana_zone(
            card,
            player,
            inferred_usage_type,
        ):
            return False

    races_ja = _as_list(
        spec.get("race_ja")
    )
    if races_ja:
        card_races_ja = {
            str(race)
            for race in _as_list(
                _card_races_ja(
                    card,
                    usage_type=inferred_usage_type,
                )
            )
        }
        if not any(
            str(expected) in actual
            for expected in races_ja
            for actual in card_races_ja
        ):
            return False

    exact_cost = _resolve_value(
        spec.get(
            "exact_cost",
            spec.get("cost"),
        ),
        context,
    )
    if exact_cost is not None:
        if _card_cost(
            card,
            usage_type=inferred_usage_type,
        ) != exact_cost:
            return False

    min_cost = spec.get("min_cost")
    if min_cost is not None:
        if _card_cost(
            card,
            usage_type=inferred_usage_type,
        ) < _resolve_value(
            min_cost,
            context,
        ):
            return False

    max_cost = _resolve_value(
        spec.get("max_cost"),
        context,
    )
    if max_cost is not None:
        if _card_cost(
            card,
            usage_type=inferred_usage_type,
        ) > max_cost:
            return False

    cost_less_than = _resolve_value(
        spec.get(
            "cost_less_than",
            spec.get("cost_lt"),
        ),
        context,
    )
    if cost_less_than is not None:
        if _card_cost(
            card,
            usage_type=inferred_usage_type,
        ) >= cost_less_than:
            return False

    exact_power = _resolve_value(
        spec.get(
            "exact_power",
            spec.get("power"),
        ),
        context,
    )
    if exact_power is not None:
        if _card_power(
            card,
            usage_type=inferred_usage_type,
        ) != exact_power:
            return False

    min_power = spec.get("min_power")
    if min_power is not None:
        if _card_power(
            card,
            usage_type=inferred_usage_type,
        ) < _resolve_value(
            min_power,
            context,
        ):
            return False

    max_power = spec.get("max_power")
    if max_power is not None:
        if _card_power(
            card,
            usage_type=inferred_usage_type,
        ) > _resolve_value(
            max_power,
            context,
        ):
            return False

    return True


def _matches_exclude_spec(
    card,
    spec,
    context,
):
    excluded = _as_list(
        spec.get("exclude")
    )
    if not excluded:
        return True

    source_card = (
        context.get("source_card")
        if context
        else None
    )

    for value in excluded:
        if value == "self" and card is source_card:
            return False
        if value == "evolution" and getattr(
            card,
            "is_evolution",
            False,
        ):
            return False

    return True


def _matches_type_spec(
    card,
    spec,
    usage_type,
):
    values = _as_list(
        spec.get(
            "types",
            spec.get(
                "card_types",
                spec.get(
                    "card_type",
                    spec.get("type"),
                ),
            ),
        )
    )

    if not values:
        return True

    return any(
        _matches_type(
            card,
            value,
            usage_type=usage_type,
        )
        for value in values
    )


def _matches_type(
    card,
    value,
    usage_type=None,
):
    key = str(value).lower()

    if key == "any":
        return True

    if key == "element":
        return bool(
            getattr(
                card,
                "is_element",
                False,
            )
        )

    if key == "creature":
        return is_creature_card(card)

    if key == "spell":
        return _is_spell_card(card)

    if key == "non_creature":
        return (
            not _matches_type(
                card,
                "creature",
                usage_type=usage_type,
            )
            or (
                isinstance(
                    card,
                    TwinPactCard,
                )
                and card.spell_face is not None
            )
        )

    card_type = CARD_TYPE_NAMES.get(key)
    if card_type is None:
        raise ValueError(f"Unknown card type filter: {value}")

    return card.has_card_type(card_type)


def _is_spell_card(
    card,
):
    if is_card_pending(card):
        return False

    if is_seal_card(card):
        return False

    if isinstance(
        card,
        SpellCard,
    ):
        return True

    return (
        isinstance(card, TwinPactCard)
        and card.spell_face is not None
    )


def _usage_type_from_spec(
    spec,
):
    value = spec.get(
        "type",
        spec.get("card_type"),
    )
    if isinstance(
        value,
        str,
    ):
        return value

    return None


def _card_cost(
    card,
    usage_type=None,
):
    if is_seal_card(card):
        return 0

    if isinstance(
        card,
        TwinPactCard,
    ):
        key = (
            str(usage_type).lower()
            if usage_type is not None
            else None
        )
        if key in (
            "element",
            "creature",
        ):
            return card.creature_face.cost
        if key in (
            "spell",
            "non_creature",
        ):
            return card.spell_face.cost
        if card.selected_face is not None:
            return card.selected_face.cost

    get_current_cost = getattr(
        card,
        "get_current_cost",
        None,
    )
    if get_current_cost is not None:
        try:
            return get_current_cost()
        except ValueError:
            pass

    return card.cost


def _resolve_filter_player(
    value,
    context,
):
    """フィルタ用のプレイヤー参照を解決する。

    ``True`` / ``"self"`` / ``"controller"`` / ``"owner"`` はいずれも
    フィルタを評価しているプレイヤー（context["player"]）を指す。
    """

    context = context or {}
    if value in (
        True,
        "self",
        "controller",
        "owner",
    ):
        return context.get("player")

    if value == "opponent":
        return context.get("opponent")

    return context.get("player")


def _civilizations_all_in_mana_zone(
    card,
    player,
    usage_type=None,
):
    """カードの文明がすべて player のマナゾーンに存在するか。

    無色（文明を持たない）カードは「すべての文明（=0個）がある」とみなし True。
    """

    card_civilizations = _card_civilizations(
        card,
        usage_type=usage_type,
    )
    if not card_civilizations:
        return True

    mana_zone = getattr(
        player,
        "mana_zone",
        None,
    )
    if mana_zone is None:
        return False

    available = 0
    for mana_card in visible_cards(mana_zone.cards):
        available |= _card_civilizations(mana_card)

    return (card_civilizations & ~available) == 0


def _card_civilizations(
    card,
    usage_type=None,
):
    if is_seal_card(card):
        return 0

    if isinstance(
        card,
        TwinPactCard,
    ):
        key = (
            str(usage_type).lower()
            if usage_type is not None
            else None
        )
        if key in (
            "element",
            "creature",
        ):
            return card.creature_face.civilizations
        if key in (
            "spell",
            "non_creature",
        ):
            return card.spell_face.civilizations
        if card.selected_face is not None:
            return card.selected_face.civilizations

    return card.civilizations


def _card_races_ja(
    card,
    usage_type=None,
):
    if is_seal_card(card):
        return ()

    if isinstance(
        card,
        TwinPactCard,
    ):
        key = (
            str(usage_type).lower()
            if usage_type is not None
            else None
        )
        if key in (
            None,
            "element",
            "creature",
        ):
            return card.creature_face.race_ja

    return getattr(
        card,
        "race_ja",
        (),
    )


def _card_power(
    card,
    usage_type=None,
):
    if is_seal_card(card):
        return 0

    if isinstance(
        card,
        TwinPactCard,
    ):
        key = (
            str(usage_type).lower()
            if usage_type is not None
            else None
        )
        if key in (
            "spell",
            "non_creature",
        ):
            return 0

    get_current_power = getattr(
        card,
        "get_current_power",
        None,
    )
    if get_current_power is not None:
        return get_current_power()

    return getattr(
        card,
        "base_power",
        0,
    )


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return list(value)

    return [value]


def _resolve_value(
    value,
    context,
):
    if value == "hand_size":
        player = (
            context.get("player")
            if context
            else None
        )
        if player is None:
            return None

        return len(
            visible_cards(
                player.hand.cards
            )
        )

    if value == "own_mana_zone_count":
        player = (
            context.get("player")
            if context
            else None
        )
        if player is None:
            return None

        return len(
            visible_cards(
                player.mana_zone.cards
            )
        )

    if not isinstance(
        value,
        dict,
    ):
        return value

    if value.get("type") == "hand_size":
        player = (
            context.get("player")
            if context
            else None
        )
        if player is None:
            return None

        return len(
            visible_cards(
                player.hand.cards
            )
        )

    if value.get("from") == "stored":
        key = value["key"]
        card = context.get(
            key
        ) if context else None

        if card is None:
            return None

        if value.get("field") == "creature_cost":
            return creature_cost(card)

        if value.get("field") == "cost":
            return _card_cost(card)

        if value.get("field") == "power":
            return _card_power(card)

    raise ValueError(f"Unsupported dynamic value: {value}")
