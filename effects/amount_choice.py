"""Helpers for resolving fixed and optional effect amounts."""


def resolve_effect_amount(
    *,
    game,
    player,
    amount=1,
    min_amount=None,
    max_amount=None,
    prompt=None,
):
    """Return a concrete amount for fixed or "up to N" effect specs."""
    if max_amount is None:
        return amount

    minimum = 0 if min_amount is None else int(min_amount)
    maximum = int(max_amount)
    if maximum < minimum:
        raise ValueError(
            "max_amount must be greater than or equal to min_amount"
        )

    selected = game.choice_manager.select(
        player,
        list(range(minimum, maximum + 1)),
        prompt=prompt or f"Choose an amount up to {maximum}",
        min_count=1,
        max_count=1,
    )

    if selected is None:
        return minimum

    if isinstance(selected, list):
        selected = selected[0] if selected else minimum

    selected = int(selected)
    if selected < minimum or selected > maximum:
        raise ValueError(f"Selected amount out of range: {selected}")

    return selected
