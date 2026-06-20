"""Dスイッチ（D2フィールドのキーワード能力）。

Dスイッチは「[カードごとに異なる誘発タイミング]の時、このD2フィールドをゲーム中で
1度上下逆さまにしてもよい。そうしたら、[カードごとに異なる後続効果]を使ってもよい」
という共通メカニクス。カードによって**誘発も後続効果も違う**ため、`trigger` と
`effects` を JSON 側で指定し、ここでは共通部分だけを組み立てる。

共通部分:
  - **展開中1度**: フィールドの ``d_switch_flipped`` が立っていれば誘発しない
    （`source_has_state` 条件）。反転は `flip_d2_field` 効果が立てる。カード表記は
    「ゲーム中で1度」だが、D2フィールドはバトルゾーンを離れると反転状態がリセット
    される（`FieldCard.reset_battle_state`）ため、再展開すれば再び使える。
  - **「上下逆さまにして（そうしたら）後続」**: 先頭に `flip_d2_field`（任意の反転）、
    続けて後続効果を `connector: "then"` の packaged で繋ぎ、**反転した時だけ**後続を
    実行する。

JSON 例（keyword グループに object で置く）::

    {
      "ability_id": "d_switch",
      "label": "Dスイッチ：...",
      "trigger": {"event": "attack_declared", "target": "controller"},
      "flip_prompt": "このD2フィールドを上下逆さまにしますか？",
      "effects": [ ... 後続効果 ... ]
    }
"""

from abilities.v2.json_triggered_ability import JsonTriggeredAbility


def build_d_switch_ability(
    spec,
    card,
    game,
):
    if "trigger" not in spec:
        raise ValueError(
            f"d_switch requires a trigger: {spec}"
        )

    # 展開中1度: 既に反転済みなら誘発しない（離れるとリセットされ再展開で再使用可）。
    flip_guard = {
        "type": "source_has_state",
        "state": "d_switch_flipped",
        "value": False,
    }
    user_condition = spec.get("condition")
    if user_condition is not None:
        condition = {
            "type": "and",
            "conditions": [
                flip_guard,
                user_condition,
            ],
        }
    else:
        condition = flip_guard

    follow_up_effects = spec.get("effects", [])

    triggered_spec = {
        "ability_id": "d_switch",
        "label": spec.get("label", "Dスイッチ"),
        "trigger": spec["trigger"],
        "condition": condition,
        "effects": [
            {
                "effect_id": "flip_d2_field",
                "prompt": spec.get("flip_prompt"),
            },
            {
                "effect_id": "packaged",
                "connector": "then",
                "effects": follow_up_effects,
            },
        ],
    }

    return JsonTriggeredAbility(
        card,
        game,
        triggered_spec,
    )
