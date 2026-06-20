"""Generic conditional alternative summon cost ability."""

from abilities.base.base_ability import BaseAbility
from actions.destroy_action import DestroyAction
from actions.summon_action import SummonAction
from cards.card import Civilization
from cards.creature_card import CreatureCard
from cards.twin_pact_card import TwinPactCard
from zones.zone_type import ZoneType
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


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
    "deck": ZoneType.DECK,
    "grave": ZoneType.GRAVEYARD,
    "graveyard": ZoneType.GRAVEYARD,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "mana_zone": ZoneType.MANA,
    "shield": ZoneType.SHIELD,
    "shield_zone": ZoneType.SHIELD,
}


class AlternativeSummonCostAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        active_zone,
        cost,
        civilizations=None,
        additional_costs=None,
        requirements=None,
        conditions=None,
        label=None,
    ):

        super().__init__()
        self.owner_card = owner_card
        self.active_zone = active_zone
        self.cost = cost
        self.civilizations = _civilization_bits(
            civilizations
        )
        self.additional_costs = tuple(
            additional_costs or ()
        )
        if requirements is None:
            requirements = conditions
        self.requirements = tuple(
            requirements or ()
        )
        self.label = label or "alternative summon cost"

    def get_alternative_summon_actions(
        self,
        player,
        card,
    ):

        if not self.can_pay(
            player,
            card,
        ):
            return []

        return [
            SummonAction(
                player,
                card,
                alternative_cost=self,
            )
        ]

    def can_pay(
        self,
        player,
        card,
    ):

        if card is not self.owner_card:
            return False

        if getattr(
            card,
            "zone",
            None,
        ) != self.active_zone:
            return False

        if not all(
            _requirement_met(
                requirement,
                player,
            )
            for requirement in self.requirements
        ):
            return False

        if any(
            not _additional_cost_can_pay(
                additional_cost,
                player,
            )
            for additional_cost in self.additional_costs
        ):
            return False

        return player.can_pay_cost(
            self.cost,
            self.civilizations,
            spending_card=card,
        )

    def pay(
        self,
        game,
        player,
        card,
    ):

        if not self.can_pay(
            player,
            card,
        ):
            return False

        for additional_cost in self.additional_costs:
            if not _pay_additional_cost(
                additional_cost,
                game,
                player,
                card,
            ):
                return False

        return player.tap_mana(
            self.cost,
            spending_card=card,
            required_civilizations=(
                self.civilizations
            ),
            choice_manager=(
                game.choice_manager
            ),
        )


def build_alternative_summon_cost_ability(
    spec,
    card,
):

    return AlternativeSummonCostAbility(
        owner_card=card,
        active_zone=_zone_type(
            spec.get(
                "active_zone",
                spec.get(
                    "source_zone",
                    "hand",
                ),
            )
        ),
        cost=spec.get(
            "cost",
            spec.get(
                "mana_cost",
                0,
            ),
        ),
        civilizations=spec.get(
            "civilizations",
            spec.get("civilization"),
        ),
        additional_costs=_normalize_list(
            spec.get(
                "additional_costs",
                spec.get("additional_cost"),
            )
        ),
        requirements=_requirements(spec),
        label=spec.get("label"),
    )


def _requirements(
    spec,
):

    requirements = _normalize_list(
        spec.get(
            "requirements",
            spec.get("conditions"),
        )
    )

    min_shields = spec.get(
        "min_shields",
        spec.get("shield_count"),
    )
    if min_shields is not None:
        requirements.append(
            {
                "id": "min_shields",
                "count": min_shields,
            }
        )

    return requirements


def _requirement_met(
    requirement,
    player,
):

    requirement_id = requirement.get("id")

    if requirement_id == "min_shields":
        shield_count = getattr(
            player.shield_zone,
            "shield_count",
            None,
        )
        actual = (
            shield_count()
            if shield_count is not None
            else sum(
                1
                for card in player.shield_zone.cards
                if not is_card_pending(card)
            )
        )
        return (
            actual
            >= requirement.get(
                "count",
                0,
            )
        )

    raise ValueError(
        f"Unknown alternative summon requirement: {requirement_id}"
    )


def _additional_cost_can_pay(
    spec,
    player,
):

    cost_id = spec.get("id")

    if cost_id == "destroy_own_creature":
        return bool(
            _own_creature_candidates(player)
        )

    raise ValueError(
        f"Unknown additional cost: {cost_id}"
    )


def _pay_additional_cost(
    spec,
    game,
    player,
    card,
):

    cost_id = spec.get("id")

    if cost_id == "destroy_own_creature":
        target = game.choice_manager.select(
            player,
            _own_creature_candidates(player),
            prompt=spec.get(
                "prompt",
                (
                    "Choose one of your creatures to destroy "
                    f"for {card.name}"
                ),
            ),
        )

        if target is None:
            return False

        game.action_processor.process(
            DestroyAction(
                player,
                target,
            )
        )
        return True

    raise ValueError(
        f"Unknown additional cost: {cost_id}"
    )


def _own_creature_candidates(
    player,
):

    return [
        card
        for card in player.battle_zone.cards
        if getattr(
            card,
            "owner",
            None,
        ) is player
        and not is_card_pending(card)
        and not is_seal_card(card)
        and not is_ignored_by_seal(card)
        and _is_creature(card)
    ]


def _is_creature(
    card,
):

    if isinstance(
        card,
        CreatureCard,
    ):
        return True

    return (
        isinstance(card, TwinPactCard)
        and isinstance(
            getattr(
                card,
                "selected_face",
                None,
            ),
            CreatureCard,
        )
    )


def _normalize_list(
    value,
):

    if value is None:
        return []

    if isinstance(value, list):
        return list(value)

    return [
        value,
    ]


def _zone_type(
    value,
):

    if isinstance(value, ZoneType):
        return value

    key = str(value).lower()
    if key not in ZONE_TYPES:
        raise ValueError(
            f"Unknown alternative summon active_zone: {value}"
        )

    return ZONE_TYPES[key]


def _civilization_bits(
    values,
):

    if values is None:
        return 0

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

