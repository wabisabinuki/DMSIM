"""Small predicates for the seal mechanic."""


def is_seal_card(card):
    return bool(
        getattr(
            card,
            "is_seal",
            False,
        )
    )


def is_ignored_by_seal(card):
    if not getattr(
        card,
        "is_ignored_by_seal",
        False,
    ):
        return False

    zone = getattr(
        card,
        "zone",
        None,
    )
    return getattr(
        zone,
        "name",
        None,
    ) == "BATTLE"


def has_attached_seals(card):
    return bool(
        getattr(
            card,
            "seals",
            (),
        )
    )
