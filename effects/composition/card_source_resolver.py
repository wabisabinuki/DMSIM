"""Resolve card collections used by generic composition effects."""

from core.effect_argument_resolver import EffectArgumentResolver
from core.pending_cards import visible_cards
from core.seal_utils import is_ignored_by_seal
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


STORED_SOURCES = (
    "stored",
    "selected",
    "selected_cards",
    "selected_targets",
)
ZONE_SOURCES = (
    "zone",
    "zone_cards",
)


def resolve_card_source(
    spec,
    game,
    player,
    source_card=None,
    package_context=None,
    default_source=None,
):
    package_context = package_context or {}

    if "cards" in spec:
        context = EffectArgumentResolver(game).context(
            player,
            source_card=source_card,
            package_context=package_context,
        )
        return EffectArgumentResolver(game).cards(
            spec["cards"],
            context,
        )

    source = spec.get("source", default_source)
    if isinstance(source, dict):
        return _resolve_structured_source(
            source,
            spec,
            game,
            player,
            source_card,
            package_context,
        )

    if source in STORED_SOURCES:
        return _stored_cards(
            package_context,
            _source_key(spec),
        )

    if source in ZONE_SOURCES or "zone" in spec:
        return _zone_cards(
            spec,
            game,
            player,
            source_card,
            package_context,
        )

    if source is None:
        key = _source_key(spec)
        if key is not None:
            return _stored_cards(
                package_context,
                key,
            )
        return []

    return _stored_cards(
        package_context,
        source,
    )


def _resolve_structured_source(
    source,
    spec,
    game,
    player,
    source_card,
    package_context,
):
    source_type = source.get(
        "source",
        source.get("from"),
    )
    merged = {
        **spec,
        **source,
    }

    if source_type in STORED_SOURCES:
        return _stored_cards(
            package_context,
            _source_key(merged),
        )

    if source_type in ZONE_SOURCES or "zone" in source:
        return _zone_cards(
            merged,
            game,
            player,
            source_card,
            package_context,
        )

    if "ref" in source:
        context = EffectArgumentResolver(game).context(
            player,
            source_card=source_card,
            package_context=package_context,
        )
        return _as_cards(
            EffectArgumentResolver(game).value(
                source,
                context,
            )
        )

    return _stored_cards(
        package_context,
        _source_key(merged),
    )


def _source_key(spec):
    return spec.get(
        "store_key",
        spec.get(
            "key",
            spec.get(
                "source_key",
                spec.get("store_as"),
            ),
        ),
    )


def _stored_cards(
    package_context,
    key,
):
    if key is None:
        return []

    return _as_cards(
        package_context.get(key)
    )


def _zone_cards(
    spec,
    game,
    player,
    source_card,
    package_context,
):
    args = EffectArgumentResolver(game)
    context = args.context(
        player,
        source_card=source_card,
        package_context=package_context,
    )
    owner = args.player(
        spec.get("player", spec.get("target_player", "self")),
        context,
    )
    zone = parse_zone(
        args.value(
            spec.get("zone"),
            context,
        )
    )

    cards = list(
        owner.get_zone(zone).cards
    )
    if zone != ZoneType.SHIELD:
        cards = visible_cards(cards)
    else:
        cards = [
            card
            for card in cards
            if not getattr(card, "is_pending", False)
        ]

    cards = [
        card
        for card in cards
        if not is_ignored_by_seal(card)
    ]

    position = spec.get("from", spec.get("position"))
    amount = spec.get("amount")
    if amount is None:
        return cards

    amount = args.value(
        amount,
        context,
    )
    if amount == "all":
        return cards

    amount = int(amount)
    if position in (
        "bottom",
        "last",
    ):
        return cards[-amount:] if amount > 0 else []

    return cards[:amount]


def _as_cards(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [
            item
            for item in value
            if item is not None
            and not is_ignored_by_seal(item)
        ]

    if is_ignored_by_seal(value):
        return []

    return [value]
