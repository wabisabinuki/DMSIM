"""Mana payment search and selection helpers."""

from dataclasses import dataclass

from cards.card import Civilization


CIVILIZATION_ORDER = (
    Civilization.FIRE,
    Civilization.WATER,
    Civilization.NATURE,
    Civilization.LIGHT,
    Civilization.DARKNESS,
)


@dataclass(frozen=True)
class ManaPaymentSelection:
    card: object
    civilization: int | None = None


def civilization_bits(civilizations):
    return [
        bit
        for bit in CIVILIZATION_ORDER
        if civilizations & bit
    ]


def card_civilizations(card):
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


def can_complete_payment(
    cost,
    remaining_civilizations,
    paid,
    available_cards,
    mana_value,
    mana_civilizations=card_civilizations,
):
    if paid + _total_value(
        available_cards,
        mana_value,
    ) < cost:
        return False

    return _can_assign_civilizations(
        list(remaining_civilizations),
        available_cards,
        mana_civilizations,
    )


def can_pay_with_mana(
    cost,
    required_civilizations,
    available_cards,
    mana_value,
    mana_civilizations=card_civilizations,
):
    return can_complete_payment(
        cost,
        civilization_bits(required_civilizations),
        0,
        available_cards,
        mana_value,
        mana_civilizations,
    )


def auto_select_mana(
    cost,
    required_civilizations,
    available_cards,
    mana_value,
    mana_civilizations=card_civilizations,
):
    if not can_pay_with_mana(
        cost,
        required_civilizations,
        available_cards,
        mana_value,
        mana_civilizations,
    ):
        return None

    required_bits = civilization_bits(
        required_civilizations
    )
    selected = []
    used = set()

    if not _assign_for_auto(
        required_bits,
        0,
        available_cards,
        used,
        selected,
        mana_civilizations,
    ):
        return None

    paid = payment_total(
        selected,
        mana_value,
    )

    for card in available_cards:
        if paid >= cost:
            break

        if id(card) in used:
            continue

        selected.append(
            ManaPaymentSelection(card)
        )
        used.add(id(card))
        paid += mana_value(card)

    if paid < cost:
        return None

    return selected


def civilization_candidates(
    cost,
    civilization,
    remaining_civilizations,
    paid,
    available_cards,
    mana_value,
    mana_civilizations=card_civilizations,
):
    candidates = []

    for card in available_cards:
        if not mana_civilizations(card) & civilization:
            continue

        remaining_cards = [
            other
            for other in available_cards
            if other is not card
        ]
        next_paid = paid + mana_value(card)

        if not can_complete_payment(
            cost,
            remaining_civilizations,
            next_paid,
            remaining_cards,
            mana_value,
            mana_civilizations,
        ):
            continue

        candidates.append(
            ManaPaymentSelection(
                card,
                civilization,
            )
        )

    return candidates


def remaining_mana_candidates(
    cost,
    paid,
    available_cards,
    mana_value,
):
    candidates = []

    for card in available_cards:
        remaining_cards = [
            other
            for other in available_cards
            if other is not card
        ]
        next_paid = paid + mana_value(card)

        if not can_complete_payment(
            cost,
            (),
            next_paid,
            remaining_cards,
            mana_value,
        ):
            continue

        candidates.append(
            ManaPaymentSelection(card)
        )

    return candidates


def payment_total(
    selections,
    mana_value,
):
    return sum(
        mana_value(selection.card)
        for selection in selections
    )


def is_valid_payment(
    selections,
    cost,
    required_civilizations,
    available_cards,
    mana_value,
    mana_civilizations=card_civilizations,
):
    available_ids = {
        id(card)
        for card in available_cards
    }
    used_ids = set()

    for selection in selections:
        card = selection.card
        key = id(card)

        if key not in available_ids:
            return False

        if key in used_ids:
            return False

        used_ids.add(key)

        civilization = selection.civilization
        if civilization is None:
            continue

        if not mana_civilizations(card) & civilization:
            return False

    paid_civilizations = {
        selection.civilization
        for selection in selections
        if selection.civilization is not None
    }

    for required in civilization_bits(
        required_civilizations
    ):
        if required not in paid_civilizations:
            return False

    return payment_total(
        selections,
        mana_value,
    ) >= cost


def normalize_selections(
    selections,
):
    normalized = []

    for selection in selections:
        if isinstance(
            selection,
            ManaPaymentSelection,
        ):
            normalized.append(selection)
        else:
            normalized.append(
                ManaPaymentSelection(selection)
            )

    return normalized


def _assign_for_auto(
    required_bits,
    index,
    available_cards,
    used,
    selected,
    mana_civilizations=card_civilizations,
):
    if index == len(required_bits):
        return True

    required = required_bits[index]

    for card in available_cards:
        key = id(card)
        if key in used:
            continue

        if not mana_civilizations(card) & required:
            continue

        used.add(key)
        selected.append(
            ManaPaymentSelection(
                card,
                required,
            )
        )

        if _assign_for_auto(
            required_bits,
            index + 1,
            available_cards,
            used,
            selected,
            mana_civilizations,
        ):
            return True

        selected.pop()
        used.remove(key)

    return False


def _can_assign_civilizations(
    required_bits,
    available_cards,
    mana_civilizations=card_civilizations,
):
    if not required_bits:
        return True

    used = set()

    def dfs(index):
        if index == len(required_bits):
            return True

        required = required_bits[index]

        for card in available_cards:
            key = id(card)
            if key in used:
                continue

            if not mana_civilizations(card) & required:
                continue

            used.add(key)
            if dfs(index + 1):
                return True
            used.remove(key)

        return False

    return dfs(0)


def _total_value(
    cards,
    mana_value,
):
    return sum(
        mana_value(card)
        for card in cards
    )
