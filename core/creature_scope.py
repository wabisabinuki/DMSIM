"""Helpers for abilities and effects that target creature groups."""


def matches_creature_scope(
    scope,
    source_card,
    card,
    owner=None,
    target_card=None,
):
    if scope in (
        "own_creature",
        "own_creatures",
    ):
        return owner == source_card.owner

    if scope == "own_other_creatures":
        return (
            owner == source_card.owner
            and card is not source_card
        )

    if scope == "self":
        return card is source_card

    if scope == "target_creature":
        return card is target_card

    if scope == "opponent_creatures":
        return owner != source_card.owner

    if scope == "creatures":
        return True

    raise ValueError(
        f"Unknown creature scope: {scope}"
    )


def creatures_for_scope(
    game,
    scope,
    source_card,
    target_card=None,
):
    creatures = game.query.get_creatures()
    return [
        creature
        for creature in creatures
        if matches_creature_scope(
            scope,
            source_card,
            creature,
            owner=creature.owner,
            target_card=target_card,
        )
    ]
