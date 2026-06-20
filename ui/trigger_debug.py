"""
イベントの購読と能力トリガー、効果解決状況に特化してデバッグログを追跡・出力するデバッグツール。
"""

"""誘発・効果解決のデバッグ表示"""

from ui.debug_log import debug_print, is_debug_enabled


def _card_label(card):

    if card is None:
        return "—"

    return getattr(card, "name", str(card))


def _ability_label(ability):

    name = type(ability).__name__
    card = getattr(ability, "owner_card", None)

    if card is not None:
        return f"{name} ({_card_label(card)})"

    return name


def _ability_trigger_label(ability):

    return (
        getattr(ability, "label", None)
        or _ability_label(ability)
    )


def _effect_label(effect):

    return (
        getattr(effect, "label", None)
        or type(effect).__name__
    )


def log_trigger(
    event,
    ability,
    effects,
):

    timing = type(event).__name__

    if not is_debug_enabled():
        if effects:
            card = getattr(
                ability,
                "owner_card",
                None,
            )
            if card is not None:
                print(
                    f"誘発: {_card_label(card)} | "
                    f"{_ability_trigger_label(ability)}"
                )
                return

            print(
                f"誘発: {_ability_trigger_label(ability)}"
            )
        return

    debug_print(
        f"[Trigger] 誘発タイミング: {timing}"
    )
    debug_print(
        f"          誘発能力: "
        f"{_ability_label(ability)}"
    )

    if not effects:
        debug_print("          生成効果: (なし)")
        return

    for index, effect in enumerate(
        effects,
        start=1,
    ):
        debug_print(
            f"          生成効果[{index}]: "
            f"{type(effect).__name__}"
        )


def log_turn_trigger_batch(
    event_type,
    turn_player,
    count,
):

    debug_print(
        f"[TurnTrigger] 誘発タイミング: "
        f"{event_type.__name__} "
        f"({turn_player.name}) "
        f"- {count}件を順に処理"
    )


def log_turn_trigger_skip(
    ability,
    reason,
):

    debug_print(
        f"[TurnTrigger]   スキップ: "
        f"{_ability_label(ability)} "
        f"({reason})"
    )


def log_spell_effects(
    spell,
    effects,
):

    debug_print(
        f"[Trigger] 誘発タイミング: "
        f"CastSpell ({_card_label(spell)})"
    )

    if not effects:
        debug_print("          生成効果: (なし)")
        return

    for index, effect in enumerate(
        effects,
        start=1,
    ):
        debug_print(
            f"          生成効果[{index}]: "
            f"{type(effect).__name__}"
        )


def log_shield_trigger_enqueue(
    card,
):

    debug_print(
        "[Trigger] シールドチェック"
    )
    debug_print(
        f"          S・トリガー候補: "
        f"{_card_label(card)}"
    )


def log_g_strike_enqueue(
    card,
):

    debug_print(
        "[Trigger] シールドチェック"
    )
    debug_print(
        f"          G・ストライク公開: "
        f"{_card_label(card)}"
    )


def log_shield_trigger_play(
    card,
):

    debug_print(
        f"[Resolve] シールドチェック: "
        f"S・トリガー使用: "
        f"{_card_label(card)}"
    )


def log_g_strike_play(
    card,
    target=None,
):

    if target is None:
        debug_print(
            f"[Resolve] シールドチェック: "
            f"G・ストライク使用なし: "
            f"{_card_label(card)}"
        )
        return

    debug_print(
        f"[Resolve] シールドチェック: "
        f"G・ストライク使用: "
        f"{_card_label(card)} -> "
        f"{_card_label(target)}"
    )


def log_effect_resolve(
    effect,
    *,
    skipped=False,
    reason=None,
):

    name = type(effect).__name__
    label = _effect_label(effect)
    source = getattr(
        effect,
        "source_card",
        None,
    )

    if source is not None:
        detail = (
            f"{label} "
            f"(誘発元: {_card_label(source)})"
        )
    else:
        detail = label

    if skipped:
        debug_print(
            f"[Resolve] スキップ: {detail}"
            f" - {reason}"
        )
        return

    if is_debug_enabled():
        debug_print(
            f"[Resolve] 解決: {detail}"
        )
        return

    if source is not None:
        print(
            f"効果発動: {_card_label(source)} | {label}"
        )
        return

    print(
        f"効果発動: {label}"
    )
