"""Helpers for recording card plays."""


def record_play(
    game,
    player,
    card,
    action_type,
    from_zone,
    action,
):
    record = {
        "turn": game.state.turn,
        "player": player,
        "card": card,
        "action_type": action_type,
        "from_zone": from_zone,
        "play_method": getattr(
            action,
            "play_method",
            None,
        ),
        "cost_mode": getattr(
            action,
            "cost_mode",
            None,
        ),
        "cost_skipped": bool(
            getattr(
                action,
                "ignore_cost",
                False,
            )
        ),
        "paid_cost": not bool(
            getattr(
                action,
                "ignore_cost",
                False,
            )
        ),
    }

    game.state.play_history.append(record)

    if not hasattr(
        card,
        "play_history",
    ):
        card.play_history = []

    card.play_history.append(record)
    card.last_play_record = record
    return record
