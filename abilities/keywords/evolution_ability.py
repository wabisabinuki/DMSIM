"""Evolution keyword ability definitions."""

from abilities.base.base_ability import BaseAbility
from cards.card import CardType, Civilization
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


CIVILIZATION_BITS = {
    "fire": Civilization.FIRE,
    "water": Civilization.WATER,
    "nature": Civilization.NATURE,
    "light": Civilization.LIGHT,
    "darkness": Civilization.DARKNESS,
}

ZONE_TYPES = {
    "battle": ZoneType.BATTLE,
    "battle_zone": ZoneType.BATTLE,
    "grave": ZoneType.GRAVEYARD,
    "graveyard": ZoneType.GRAVEYARD,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "mana_zone": ZoneType.MANA,
}


class EvolutionAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        source_zone=ZoneType.BATTLE,
        source_count=1,
        civilizations=None,
        card_types=None,
        label=None,
    ):

        super().__init__()
        self.owner_card = owner_card
        self.source_zone = source_zone
        self.source_count = source_count
        self.civilizations = _civilization_bits(civilizations)
        self.card_types = _card_types(card_types)
        self.label = label

    def source_candidates(
        self,
        player,
        card,
    ):

        zone = player.get_zone(
            self.source_zone
        )
        return [
            candidate
            for candidate in zone.cards
            if candidate is not card
            and not is_card_pending(candidate)
            and self.can_use_as_source(
                candidate
            )
        ]

    def can_use_as_source(
        self,
        candidate,
    ):

        if self.card_types and not any(
            candidate.has_card_type(card_type)
            for card_type in self.card_types
        ):
            return False

        if (
            self.civilizations is not None
            and not candidate.civilizations & self.civilizations
        ):
            return False

        return True


def build_evolution_ability(
    spec,
    card,
):

    return EvolutionAbility(
        owner_card=card,
        source_zone=_zone_type(
            spec.get(
                "source_zone",
                "battle",
            )
        ),
        source_count=spec.get(
            "source_count",
            spec.get(
                "count",
                1,
            ),
        ),
        civilizations=spec.get(
            "civilizations",
            spec.get("civilization"),
        ),
        card_types=spec.get(
            "card_types",
            spec.get(
                "card_type",
                "creature",
            ),
        ),
        label=spec.get("label"),
    )


def _zone_type(
    value,
):

    if isinstance(value, ZoneType):
        return value

    key = str(value).lower()
    if key not in ZONE_TYPES:
        raise ValueError(
            f"Unknown evolution source_zone: {value}"
        )

    return ZONE_TYPES[key]


def _civilization_bits(
    values,
):

    if values is None:
        return None

    if isinstance(values, str):
        values = [values]

    bits = 0
    for value in values:
        key = str(value).lower()
        if key not in CIVILIZATION_BITS:
            raise ValueError(
                f"Unknown civilization: {value}"
            )
        bits |= CIVILIZATION_BITS[key]

    return bits


def _card_types(
    values,
):

    if values is None:
        return None

    if isinstance(values, str):
        values = [values]

    mapping = {
        "creature": CardType.CREATURE,
    }
    card_types = []
    for value in values:
        key = str(value).lower()
        if key not in mapping:
            raise ValueError(
                f"Unknown evolution card_type: {value}"
            )
        card_types.append(mapping[key])

    return tuple(card_types)
