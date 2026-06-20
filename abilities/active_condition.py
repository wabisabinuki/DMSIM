"""Shared active_if evaluator for registry-built abilities."""


def active_if_matches(
    active_if,
    owner_card,
    game,
    player=None,
    event=None,
):
    if (
        getattr(owner_card, "is_seal", False)
        or getattr(owner_card, "is_ignored_by_seal", False)
    ):
        return False

    if active_if is None:
        return True

    if active_if == "hyper_mode":
        return bool(
            getattr(
                owner_card,
                "is_hyper_mode_active",
                False,
            )
        )

    if isinstance(active_if, dict):
        from core.condition_evaluator import ConditionEvaluator

        return ConditionEvaluator(game).evaluate(
            active_if,
            {
                "game": game,
                "player": player
                or getattr(
                    owner_card,
                    "owner",
                    None,
                ),
                "controller": getattr(
                    owner_card,
                    "owner",
                    None,
                ),
                "source_card": owner_card,
                "event": event,
            },
        )

    return bool(active_if)
