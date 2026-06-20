"""シールドブレイクの 2 フェーズ（バッチ）処理。

複数シールドが同時にブレイクされる時、置換効果や「ブレイクされた時」のトリガーが
移動前の同時状態の盤面を観測できるよう、破壊バッチ（DestroyActionHandler）と同じ
2 フェーズで処理する。

  フェーズ1（試行・置換）:
    各シールドに ``ShieldBreakAttemptEvent`` を発行して置換効果を適用する。
    この時点ではどのシールドも移動しない。これにより置換効果は「同時にブレイク
    されるシールドがまだすべてシールドゾーンに残っている」盤面を観測できる。
    ``consume_remaining_breaks`` が立ったら、それ以降のシールドはブレイクしない。

  フェーズ2（通知・移動）:
    キャンセルされなかったブレイクについて、まず全ての ``ShieldBreakEvent`` を
    発行してから、一括で手札へ移動する（手札移動時の ``ZoneChangeAttemptEvent`` で
    S・トリガーが enqueue される）。

S・トリガー / G・ストライクの宣言・解決は呼び出し側が
``shield_trigger_resolver.resolve()`` で行う（このモジュールは移動までを担当）。
"""

from events.shield_break_attempt_event import ShieldBreakAttemptEvent
from events.shield_break_event import ShieldBreakEvent
from zones.zone_type import ZoneType


def break_shields_batch(
    context,
    shields,
    breaker,
):
    """``shields`` を同時ブレイクとして処理し、確定した attempt event を返す。

    ``shields`` は順序付きリスト。各シールドの ``owner`` を持ち主とみなす。
    """

    attempts = _attempt_breaks(
        context,
        shields,
        breaker,
    )
    _finalize_breaks(
        context,
        attempts,
        breaker,
    )
    return attempts


def _attempt_breaks(
    context,
    shields,
    breaker,
):

    attempts = []

    for shield in shields:
        target_player = shield.owner
        shield_cards = shield_cards_for(
            target_player,
            shield,
        )

        attempt_event = ShieldBreakAttemptEvent(
            target_player,
            shield,
            breaker,
            shield_cards=shield_cards,
        )
        context.replacement_manager.apply(
            attempt_event
        )

        if attempt_event.cancelled:
            continue

        attempts.append(attempt_event)

        if getattr(
            attempt_event,
            "consume_remaining_breaks",
            False,
        ):
            break

    return attempts


def _finalize_breaks(
    context,
    attempts,
    breaker,
):

    # まず確定した全ブレイクを通知する。この時点ではどのシールドもまだ
    # シールドゾーンに残っているため、「ブレイクされた時」のトリガーは
    # 同時状態の盤面を観測できる。
    for attempt_event in attempts:
        for broken_card in list(attempt_event.shield_cards):
            context.event_manager.publish(
                ShieldBreakEvent(
                    attempt_event.player,
                    broken_card,
                    breaker,
                )
            )

    # その後、一括で手札へ移動する。
    context.card_mover.pre_freeze_sources_for_many(
        [
            card
            for attempt_event in attempts
            for card in attempt_event.shield_cards
        ]
    )

    for attempt_event in attempts:
        context.card_mover.move(
            card=attempt_event.shield_card,
            owner=attempt_event.player,
            from_zone=ZoneType.SHIELD,
            to_zone=ZoneType.HAND,
            reason="shield_break",
        )


def shield_cards_for(
    player,
    shield,
):
    """``shield`` が属するスロットの実体カード群を返す（要塞化城は除く）。"""

    shield_cards = getattr(
        player.shield_zone,
        "shield_cards",
        None,
    )
    if shield_cards is not None:
        cards = shield_cards(shield)
        return cards or [shield]

    slot_cards = getattr(
        player.shield_zone,
        "slot_cards",
        None,
    )
    if slot_cards is not None:
        cards = slot_cards(shield)
        return cards or [shield]

    return [shield]
