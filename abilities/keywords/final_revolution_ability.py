"""ファイナル革命 / 極限（ファイナル）ファイナル革命 キーワード。

ファイナル革命:
  「このクリーチャーが『革命チェンジ』によって出た時、そのターンに自分が他の
  『ファイナル革命』を使っていなければ、〔効果〕」。
  誘発は enter_battle で reason が ``revolution_change`` のもの限定。発動条件は
  TurnStatsManager の **per-turn** 集計（stat ``final_revolutions_used``）が 0。

極限（ファイナル）ファイナル革命:
  「このクリーチャーが出た時、このゲーム中に自分が他の『ファイナル革命』を
  使っていなければ、〔効果〕」。
  誘発は enter_battle で出方を問わない（reason 不問）。発動条件は同じ集計の
  **per-game**（``scope: "game"``）が 0。

どちらも能力パッケージの先頭に ``mark_final_revolution_used`` 効果を挿し、解決時に
FinalRevolutionUsedEvent を publish して per-turn / per-game の両方の使用回数を
加算する。これにより、ターン内・ゲーム内で最初に解決した1つのファイナル革命
だけが発動できる（後続は集計が 0 でなくなり誘発条件を満たさない）。

実体は v2 の JsonTriggeredAbility を合成して返す。これにより本体効果 ``effects``
には v2 効果（choose_number / if / select 等）も legacy 効果（draw / gather_matching /
for_each_stored 等）も書ける。カードごとに異なる本体効果は spec の ``effects`` で与える。
"""

from abilities.v2.json_triggered_ability import JsonTriggeredAbility


FINAL_REVOLUTION_STAT = "final_revolutions_used"


def _mark_used_effect():
    return {
        "effect_id": "mark_final_revolution_used",
    }


def _unused_this_turn_condition():
    return {
        "type": "turn_stat",
        "stat": FINAL_REVOLUTION_STAT,
        "player": "controller",
        "op": "eq",
        "value": 0,
    }


def _unused_this_game_condition():
    return {
        "type": "turn_stat",
        "stat": FINAL_REVOLUTION_STAT,
        "scope": "game",
        "player": "controller",
        "op": "eq",
        "value": 0,
    }


def build_final_revolution_ability(
    spec,
    card,
    game,
):
    trigger = {
        "event": "enter_battle",
        "card": {
            "ref": "source",
        },
        "reason": "revolution_change",
    }
    return _build(
        spec,
        card,
        game,
        ability_id="final_revolution",
        trigger=trigger,
        condition=_unused_this_turn_condition(),
        default_label="ファイナル革命",
    )


def build_extreme_final_revolution_ability(
    spec,
    card,
    game,
):
    trigger = {
        "event": "enter_battle",
        "card": {
            "ref": "source",
        },
    }
    return _build(
        spec,
        card,
        game,
        ability_id="extreme_final_revolution",
        trigger=trigger,
        condition=_unused_this_game_condition(),
        default_label="極限ファイナル革命",
    )


def _build(
    spec,
    card,
    game,
    ability_id,
    trigger,
    condition,
    default_label,
):
    json_spec = {
        "ability_id": ability_id,
        "label": spec.get("label", default_label),
        "trigger": trigger,
        "condition": condition,
        "effects": [
            _mark_used_effect(),
            *spec.get("effects", []),
        ],
    }
    if "active_if" in spec:
        json_spec["active_if"] = spec["active_if"]

    return JsonTriggeredAbility(
        card,
        game,
        json_spec,
    )
