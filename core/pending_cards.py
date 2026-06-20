"""Helpers for cards that are temporarily pending while being used or moved."""


PENDING_LIST_EFFECT_ATTRS = (
    "power_modifiers",
    "temporary_combat_restrictions",
    "temporary_just_diver_effects",
    "temporary_turn_start_freezes",
    "temporary_untap_locks",
    "temporary_ninja_strike_return_effects",
)

PENDING_DICT_EFFECT_ATTRS = (
    "temporary_attack_permission",
)


def is_card_pending(
    card,
):

    return bool(
        getattr(
            card,
            "is_pending",
            False,
        )
    )


def begin_pending(
    card,
    reason=None,
):

    if card is None or is_card_pending(card):
        return False

    card.is_pending = True
    card.pending_origin_zone = getattr(
        card,
        "zone",
        None,
    )
    card.pending_reason = reason
    clear_pre_pending_effects(card)
    return True


def end_pending(
    card,
):

    if card is None or not is_card_pending(card):
        return False

    card.is_pending = False
    card.pending_origin_zone = None
    card.pending_reason = None
    clear_pre_pending_effects(card)
    return True


def clear_pre_pending_effects(
    card,
):

    for attr in PENDING_LIST_EFFECT_ATTRS:
        values = getattr(
            card,
            attr,
            None,
        )
        if values is not None:
            for value in values[:]:
                unapply = getattr(
                    value,
                    "unapply",
                    None,
                )
                if unapply is not None:
                    unapply()
            values.clear()

    for attr in PENDING_DICT_EFFECT_ATTRS:
        values = getattr(
            card,
            attr,
            None,
        )
        if values is not None:
            values.clear()

    lock_hyper_mode = getattr(
        card,
        "lock_hyper_mode",
        None,
    )
    if lock_hyper_mode is not None:
        lock_hyper_mode()


def visible_cards(
    cards,
):

    return [
        card
        for card in cards
        if not is_card_pending(card)
    ]


def first_visible_card(
    cards,
):

    for card in cards:
        if not is_card_pending(card):
            return card

    return None
