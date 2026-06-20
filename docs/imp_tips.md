# カード実装 Tips

カード実装・デバッグ中に得られた、JSON 定義と汎用パーツに関する知見をまとめる。

## 「山札の上からN枚を表向き→条件付きで手札→残り山札下」（look_top_choose_to_hand + filter）

`look_top_choose_to_hand` は `filter`（filter DSL）を取れる。山札の上 `amount` 枚を
見て、**filter に合うカードだけ**を手札に加える候補にし、選ばなかった／条件外の
カードはまとめて山札の下に置く（順序は複数なら選択）。`optional` で「加えてもよい」
／「加える」を切り替える。

```json
{ "effect_id": "look_top_choose_to_hand", "amount": 3,
  "filter": { "card_type": "creature", "power": { "gte": 6000 } },
  "optional": false, "prompt": "パワー6000以上のクリーチャーを1体手札に加える" }
```

- filter に合うカードが 0 枚なら何も手札に加わらず、3 枚すべて山札の下へ。
- 「攻撃の終わりに」発動は trigger `attack_ended` ＋ `attacker: { "ref": "source" }`。
- 参照: `dm26-rp2.C.74/77`（出た時・6000以上クリーチャー）、`dm26-rp2.R.26/77`
  （攻撃終わり・クリーチャー、ETB は `has_keyword: "blocker"` の相手をマナ送り）。

## 追加ターン（`grant_extra_turn` ＋ 挿入ターン処理）

「このターンの後に自分のターンを追加する」は effect **`grant_extra_turn`**
（`target_player` 既定 `self`）で表す。`GameState.pending_extra_turns` に対象
プレイヤーを積み、`TurnManager.advance_turn` → `GameState.advance_to_next_turn`
が通常の手番交代より先に取り出す。追加ターンは**正規の手番ローテーションを
消費しない挿入**で、`_extra_turn_return_index` に挿入前の手番位置を退避し、
追加ターン終了時に復元してから通常交代する。相手ターン中に得た場合は
「相手 → 自分(追加) → 自分(通常)」と連続手番になる（除去への反撃カードの肝）。
参照: `dm26-rp2.SR.S5/S11`（熱血V龍 ガイギンガ、`card_chosen` player:opponent で誘発）。

追加ターンは正規の手番ローテーションを消費しない**挿入**なので、相手ターン中に得ると
「相手 → 自分(追加) → 自分(通常) → 相手」と連続手番になる（`_extra_turn_return_index`
で挿入前の手番位置を退避→復元）。期間効果・表示との噛み合わせは次の通り:

- **汎用 `DurationEffect`**（`UNTIL_START_OF_CONTROLLER_TURN`＝「次の自分のターンの
  はじめまで」等）は `turn` カウンタ＋実際の `turn_player_index` で判定するため、
  追加ターンでも `turn` が増え `turn_player_index` が実プレイヤーを指すので、
  挿入された自分の追加ターンで正しく失効する。
- **ハイパーモード**は元々 +1/+2 の固定オフセットで失効ターンを決め打ちしていたため、
  追加ターン挿入でずれる問題があった。`hyper_mode_registered_turn`＋コントローラー
  一致方式へ変更済み（[[CAVEATS#ハイパーモード]]）。固定オフセット系の「次の自分の
  ターンまで」を新規実装する時は同様に登録ターン基準にすること。
- **表示**: 追加ターンかどうかは `GameState.is_current_turn_extra`
  （`_extra_turn_return_index is not None`）。`on_turn_start(turn, name, is_extra_turn=...)`
  で「（追加ターン）」ラベルを出す。`TurnStatsManager` 等の per-turn 集計は追加ターンの
  `TurnStartEvent` でもリセットされる。

## 「山上1枚を表向き(任意)→コスト条件なら踏み倒し(任意)→出さなければ手札」

`reveal_cards`(optional) → `type: if` (`card_matches {ref}` で踏み倒し可否) →
`type: if` (`card_matches {ref, filter:{zone:"deck"}}` でまだ山札にあるか)→手札、の
3 段で表す。ポイント:
- 公開を断ると `store_as` が `null` になり以降の `card_matches {ref}` が不成立→山上温存。
- 踏み倒し（`put_creature_from_zone` selection:top optional:true）後は対象が山札を
  離れるため、最後の「まだ deck にあるか」判定で手札行きを抑止できる（filter の
  `zone` フィールドは `card.zone.name.lower()` を返す）。
- 「エレメント」は filter `card_type: "element"`（`is_element`＝クリーチャー/フィールド
  等）。`put_creature_from_zone` はクリーチャー面のみ出すため、非クリーチャーの
  エレメントは出ず手札に回る。
参照: `dm26-rp2.SR.S5/S11`、踏み倒し分岐の素は `dm26-rp1` 臥龍（reveal_cards＋if）。

## トリガー能力を持つカードを put_battle 等で直置きするテストの注意

`CardTestHarness.put_battle` / `put_*` は CardMover を経由しないため、`card.zone`
は設定されるが **誘発能力が EventManager に購読登録されない**。`card_chosen` など
ゾーン直置き後に発火させたいトリガーは、配置後に
`card.register_abilities(harness.game.event_manager)` を明示的に呼ぶ
（`summon` 経由なら自動で登録される）。

## このターンの行動を参照する（`turn_stat` 条件 / TurnStatsManager）

「このターンにN枚引いた」「このターンにクリーチャーではないカードを実行した」等の
per-turn 条件は、`core/turn_stats_manager.py` の **TurnStatsManager** が集計し、
condition 能力語 **`turn_stat`** で参照する。マネージャーは GameController が常設し、
イベント（ドロー＝zone_change deck→hand、SpellCast、CardExecuted）で加算、
TurnStartEvent で全プレイヤー分をリセットする。

```json
{ "type": "turn_stat", "stat": "cards_drawn",
  "player": "controller", "op": "gte", "value": 2 }
```

- 集計 stat: `cards_drawn` / `spells_cast` / `non_creature_executed` /
  `creatures_attacked` / `final_revolutions_used`。新しい集計が必要なら
  TurnStatsManager に購読とカウントを足す（効果側は `stat` 名で参照）。
- **per-game 参照**: `scope: "game"` を付けるとターンでリセットされない per-game
  集計（`get_game`）を参照する。`final_revolutions_used` は per-turn / per-game の
  両方に加算され、極限ファイナル革命の「このゲーム中に〜」判定に使う。
- **「このターンに〜していなければ攻撃できない」**は static `attack_rule`
  `rule.kind: "cannot_attack_unless"` ＋ `rule.condition`（→
  `ConditionalAttackForbidAbility`）。condition が満たされない間だけ自身の攻撃を
  禁止する（`AttackValidator._is_attack_forbidden_by_continuous` が走査）。
- 参照: `dm26-rp2.C.56/77`（非クリーチャー実行）、`dm26-rp2.C.60/77`（2枚ドロー）。
- ゲームに常設の購読を足す時は、リスナー数を `[]` 前提にした既存テストに注意
  （before/after 比較に直す）。

## シールド・ゴー（`shield_go` キーワード）

「{SG} シールド・ゴー」はキーワード `shield_go`。1つの ID から**2つの能力**を生成する
（`abilities/registry.py` の `_shield_go`、リスト返却）:

1. 誘発（破壊された時）: `triggered`(event destroy, `active_zones:"any"`,
   `ignore_source_continuity:true`) で `move_card`(`from_zone:"graveyard"`,
   `to_zone:"shield"`, `selection:"source_card"`, `shield_face:"face_up"`)。
   ＝破壊→墓地→**表向きのシールド**へ。
2. 置換（表向きでシールドを離れる時）: `JsonReplacementAbility` の
   `attempt`(`from_zone:"shield"`, `card:{ref:source}`) ＋ `condition`
   (`card_state` shield_face_up true) ＋ `replace_with`(`to_zone:"graveyard"`)。
   ＝表向きシールドがブレイク等で離れる時、手札ではなく**墓地**へ。

```json
"keyword": [ "blocker", "shield_go" ]
```

- 置換は `ReplacementManager` がシールドゾーンも走査するため、SG カードが
  表向きシールドの間も有効（登録不要）。
- v2 `move` はシールドへ face_up を渡せないため、表向きシールド化は registry の
  `move_card`(`shield_face:"face_up"`) を使う。
- 参照: `dm26-rp2.C.55/77`（ブロッカー＋SG、サイクル全体をテスト）、`U.33/77`
  `U.42/77`（ガチンコ負けで自壊→SG）・`C.66/77`・`C.75/77`。

## パワー・ガチンコ・ジャッジ（`power_gachinko_judge`）

「自分と相手は山札の上から1枚を表向きにして下に置き、自分のパワーが相手以上なら
勝ち」を行う効果。勝敗で `on_win` / `on_lose` の効果列を解決する（
`effects/combat/power_gachinko_judge_effect.py`）。パワーを持たないカードは0扱い。

```json
{ "effect_id": "power_gachinko_judge",
  "optional": true,
  "prompt": "パワー・ガチンコ・ジャッジをしますか？",
  "on_win": [ { "effect_id": "add_deck_to_shield", "amount": 1 } ],
  "on_lose": [ { "effect_id": "destroy", "card": { "ref": "source" } } ] }
```

- `optional: true` で「してもよい」（実行可否を確認）。`repeat_until_lose: true` で
  「負けるか中止するまで繰り返す」（鬼丸「V」型、未使用）。
- `on_win`/`on_lose` は registry の effect_id で書く（内部 `build_effects`、
  package_context・source_card・trigger_snapshot を引き継ぐ）。
- 「破壊された時にジャッジ→勝ったら墓地から出す」は、トリガーに
  `ignore_source_continuity: true` ＋ `active_zones: "any"`、`on_win` に
  `put_creature_from_zone`(`from_zone:"graveyard"`, `selection:"source_card"`)。
- 新しい effect_id に `optional` を持たせたら `card_db/card_definition_validator.py`
  の `OPTIONAL_AWARE_EFFECT_IDS` にも登録する（忘れると `W_IGNORED_OPTIONAL`）。
- 参照: `dm26-rp2.U.30/77`（ターンはじめ→勝てばシールド）、`dm26-rp2.R.16/77`
  （破壊時→勝てば墓地からタップ蘇生）。
- テストの破壊は `action_processor.process(DestroyAction(player, card))`
  （`card_mover.move` では DestroyEvent が出ず「破壊された時」が誘発しない）。

## 封印（`attach_seal`）の付与パターン

`attach_seal` でクリーチャーに封印を付ける（`effects/zones/seal_effect.py`、
`game.seal_manager` 経由）。封印カードは `seal_player` の山札の上から供給される。
`select_then` の内部効果としても使える。

- 「相手のクリーチャーに封印（相手の山札から）」は select_then(opponent_creatures)
  ＋ `attach_seal`(`amount`, `seal_player: "target_owner"`)。
- 「自分のクリーチャーに封印（自分の山札から）」は select_then(own_creatures)
  ＋ `attach_seal`(`seal_player: "target_owner"`)。
- 封印数は `card.seals`（リスト）で確認。テストでは供給元プレイヤーの山札に
  `put_deck_top` でカードを入れておく。
- 参照: `dm26-rp2.R.25/77`（出た時 相手に封印）、`dm26-rp2.U.51/77`
  （ターン終わり 自分に封印）、`dm26-rp2.OR.OR1/OR1`（ドルマゲドンW）。
- **「封印が墓地に置かれた時」**は zone_change(to_zone graveyard) ＋ condition
  `event_zone_change_matches` の **`from_seal: true`**（封印カードがバトルゾーンを
  離れる移動に `SealManager.before_zone_change_event` が付けるマーカー）。
  `player: "controller"` を併せると「自分の封印」に限定できる。効果は v2 `move`
  で `card: {ref:"event.card"}`（墓地に置かれた時点で封印は解除済みの元カード）を
  graveyard→hand などへ動かす。参照: `dm26-rp2.C.64/77`（ドルーター）。

## 革命チェンジを持つカードの ETB 等の補助パターン

革命チェンジ（`revolution_change`）は攻撃時に手札の本体と攻撃クリーチャーを
入れ替えるキーワード。JSON は keyword に
`{ "ability_id": "revolution_change", "attack_creature": { "civilization":
"light"/["light","water"], "power": { "gte": 4000 } } }`（power 省略で文明のみ）。
入れ替え後の本体は「出た時」誘発が走るので、ETB は通常の `enter_battle` で書く。

- **「出た時、次の自分のターンまで相手はコストN以下の呪文を唱えられない」**は、
  ETB で `temporary_ability` を**自身へ付与**する（`cannot_cast_spells` は静的
  継続だが、`temporary_ability` で duration 付き付与すれば一時ロックになる）。

  ```json
  { "effect_id": "temporary_ability", "target": { "ref": "source" },
    "ability": { "id": "cannot_cast_spells", "affected_player": "opponent",
                 "max_cost": 3 },
    "duration": "until_start_of_controller_turn" }
  ```
  参照: `dm26-rp2.C.53/77`（ドレミ）。

- **「自分のターンに相手のクリーチャーが召喚以外で出た時、破壊」**は
  `enter_battle` トリガーに `subject: "opponent"` ＋ `reason: { "ne": "summon" }`、
  `condition: turn_player_is controller`、効果は `destroy`(`card: {ref:
  "event.card"}`)。`card_mover.move(to=battle)` は `publish_battle_enter` 既定 True
  で `reason` を伝播するので、踏み倒し登場（summon 以外）を拾える。
  参照: `dm26-rp2.C.68/77`（マッハ55）。

## ファイナル革命 / 極限ファイナル革命（`final_revolution` / `extreme_final_revolution` キーワード）

「ファイナル革命」は keyword に `{ "ability_id": "final_revolution", "effects":
[...] }` で書く。`effects` がカードごとの本体効果。誘発・条件・使用回数管理は
キーワードが内部で組み立てる（`abilities/keywords/final_revolution_ability.py`）。

- **ファイナル革命**: `enter_battle` で `reason == "revolution_change"`（＝革命チェンジ
  で出た）かつ自身が出た時に誘発。条件は per-turn の `turn_stat
  final_revolutions_used == 0`（そのターンに他のファイナル革命を使っていない）。
- **極限ファイナル革命**(`extreme_final_revolution`): `enter_battle` を出方を問わず
  （reason 不問で）拾う。条件は `scope: "game"` の `turn_stat
  final_revolutions_used == 0`（このゲーム中に他のファイナル革命を使っていない）。
- どちらも能力パッケージの先頭に `mark_final_revolution_used` 効果が入り、解決時に
  `FinalRevolutionUsedEvent` を publish → TurnStatsManager が per-turn / per-game の
  両方を加算する。よってターン内・ゲーム内で最初に解決した1つだけが発動できる。
  通常も極限も同じカウントを共有するため、互いをブロックする。
- DM1（烈しき切札 ドギラゴン逆）の「次の自分のターンまで負けない・離れない」継続
  保護は別途の大型 effect 待ち。キーワードの誘発/条件/使用管理だけ先行実装済み。

```json
"keyword": [
  { "ability_id": "revolution_change",
    "attack_creature": { "civilization": "fire", "power": { "gte": 4000 } } },
  { "ability_id": "final_revolution", "label": "ファイナル革命：…",
    "effects": [ { "effect_id": "draw", "amount": 1 } ] }
]
```

テスト: `tests/ability_tests/test_final_revolution.py`、テストカードは
`tmp_cards/final_revolution_cards.json`。

実装例（DM26-RP2 のファイナル革命サイクル本体）:
- **全タップ＋タップ数だけ任意ドロー**（S7）: `gather_matching`(opponent_creatures) →
  `for_each_stored`(tap) → `count_matching`(filter `tapped:true`) → `draw`
  (`amount:{from:stored,...}` ＋ `optional:true`)。`draw` は `optional:true` で
  「確定枚数 N を上限に 0〜N を選ぶ」任意ドローになる（動的 max にも対応）。
- **パワー未満を全マナ送り**（S8 ファイナル革命）: `gather_matching` の filter に
  `power:{lt:{ref:"source.power"}}` を入れ、`for_each_stored` で `move_card`
  (`to_zone:"mana"`)。`move_card` は対象の owner のマナへ送る（「持ち主の」）。
- **数字選択→同コスト全破壊**（S9 ファイナル革命）: v2 `choose_number`
  (`store_as`) → `gather_matching` の filter `cost:{eq:{ref:"<store_as>"}}`
  → `destroy_multiple`。`gather_matching` は filter 文脈に package_context を
  渡すので stored 参照（選んだ数字）を解決できる。

## look_then_distribute（山上Nを複数ゾーンへ振り分け）

`look_then_distribute` は「山札の上から N 枚を見て、`buckets` を上から順に処理し、
条件に合うカードを選んで各ゾーンへ動かし、残りを `remainder_zone` へ置く」効果。
プチョヘンザ斧（S8）の「山上3枚→エレメント最大1出し/1シールド化/残りマナ」用。

```json
{ "effect_id": "look_then_distribute", "amount": 3,
  "buckets": [
    { "to_zone": "battle", "max": 1, "optional": true,
      "filter": { "card_type": "element" }, "prompt": "出すエレメントを選ぶ" },
    { "to_zone": "shield", "count": 1, "prompt": "シールド化を選ぶ" } ],
  "remainder_zone": "mana" }
```

## 汎用部品（DM26-RP2 で追加）

- **`move_deck_top`**: 自分の山札の上から N 枚を `to_zone` へ移す。`optional:true` で
  all-or-nothing（「N枚を〜してもよい」型）。マナ加速など。
- **`summon_within_total_cost`**: `from_zones`（手札/マナ等）のクリーチャーから、コスト
  合計 `max_total_cost` 以下になるよう `max_count` 体まで逐次選択して踏み倒す。0体で打切可。
- **`gather_matching` のエレメント候補**: `opponent_elements` / `own_elements` / `elements`
  を追加。バトルゾーンの `is_element`（クリーチャー＋フィールド＋タマシード等、進化元除く）を
  集める。`cost:{eq:{ref:"<choose_number結果>"}}` 等の filter と併用。
- **`cost_execution_lock`**: 指定コストのカードを実行（プレイ）できなくする duration。
  対象（既定 opponent）に登録し、`ActionValidator` が召喚/詠唱/使用の宣言時に参照。
  `cost` は固定値か stored 参照（先の `choose_number` 結果）。`card_filter` を渡すと
  コスト一致かつフィルタ合致のカードだけを弾く（`{ "card_type": "spell" }` で「その
  コストの**呪文だけ**唱えられない」。VR.11/77「武将利と威嚇命の決断」参照）。
  フィルタ無しなら全カード（オーパーツ銃 S9 の「カードを実行できない」）。
- **継続保護**: `prevent_loss`（期間中ゲームに負けない＝デッキアウト敗北をゲート）と
  `opponent_effect_separation_guard`（相手のカードの効果による自軍クリーチャーの離脱を防ぐ）。
  「相手のカードの効果か」は **`game.state.current_effect_controller`**（EffectResolver が
  各効果解決中に設定する“解決中効果のコントローラー”。バトル/SBA/ルールでは None）で判定。
  CardMover の zone_change 防止経路がプレイヤーの `separation_guards` を参照する。
  ※ ダイレクトアタック敗北は combat 側が暫定実装のため保護対象外（combat 整備後に対応）。

## v2 効果で event のカードへ一時的な戦闘制限を付ける

`temporary_combat_restriction` は v2 効果としても書ける（`type` 指定）。
`target` に ref を渡せるので「相手のクリーチャーが出た/アンタップした時、そのクリーチャー
（`event.card`）を次の自ターンまで攻撃不可」を triggered で表現できる（S7）。

```json
{ "type": "temporary_combat_restriction", "target": { "ref": "event.card" },
  "restrictions": ["attack"], "duration": "until_start_of_controller_turn" }
```

## アンタップしているクリーチャーを攻撃できる（attack_rule `can_attack_untapped`）

通常クリーチャーはタップしているクリーチャー（とプレイヤー）しか攻撃できない。
「アンタップしているクリーチャーを攻撃できる」は static の attack_rule
`rule.kind: "can_attack_untapped"` → `AttackUntappedAbility`。

```json
{ "ability_id": "<card>_attack_untapped",
  "type": "attack_rule",
  "rule": { "kind": "can_attack_untapped" } }
```

- `AttackValidator._can_attack_target_base` が、相手クリーチャーがアンタップでも
  攻撃側の能力に `allows_attacking_untapped()` が True のものがあれば許可する。
- `active_if` で条件付きにもできる。
- 参照実装: `dm26-rp2.C.70/77`、`tests/ut/test_dm26_rp2_c70_77.py`。

## 呪文の最上位 effects は connector を honor しない（`packaged` で囲む）

呪文の `effects` 配列は `CastSpellActionHandler` が **1 つずつ独立に**
effect_resolver へ積む（共有 package_context のみ）。そのため最上位効果間の
**`connector: "then"` は効かない**（直前がスキップされても次が走る）。
「選んだら〜する」のような依存連鎖は `packaged` で 1 つにまとめ、その中で
`connector: "then"` を使う。

```json
"effects": [
  { "effect_id": "packaged",
    "effects": [
      { "effect_id": "select_then", "optional": true, "store_as": "t", ... },
      { "effect_id": "temporary_ability", "target": { "ref": "t" },
        "connector": "then", ... }
    ] }
]
```

- 囲まないと、select をスキップして `store_as` が未設定のまま後続が走り、
  `ref` 解決で `Unknown ref root` 例外になる。
- 「選んだ対象へ registry 能力を一時付与（攻撃誘導など）」は select_then の内部
  効果では扱えない（`bounce`/`destroy`/`tap`/`modify_power`/`temporary_combat_
  restriction`/`battle`/`move_card` のみ）。select_then で `store_as` し、別効果
  `temporary_ability`(`target: {ref}`) で付与する。`attack_lure` 等を
  「次の自分のターンのはじめまで」付与できる。
- 参照実装: `dm26-rp2.C.77/77`、`tests/ut/test_dm26_rp2_c77_77.py`。

## パワーアタッカー（攻撃中だけパワー+N の常在型）

「パワーアタッカー+N」は**常在型**能力 `power_attacker`。攻撃宣言から攻撃終了までの
間、このクリーチャーが現在の攻撃クリーチャーであればパワーが +N される（誘発型では
ない＝シールドブレイク／バトルのいずれでも一貫して反映される）。

```json
"keyword": [ { "ability_id": "power_attacker", "amount": 3000 } ]
```

- 仕組み: `CombatManager.process_attack` が攻撃宣言時に
  **`state.current_attacker = attacker`** をセットし、`_publish_attack_ended` で
  `None` に戻す。`PowerAttackerAbility.modify_power`
  （`abilities/keywords/power_attacker_ability.py`）が
  `game.state.current_attacker is creature` の間だけ +N する。
- `active_if` も渡せる（条件付きパワーアタッカー）。
- テストは `harness.game.state.current_attacker = source` で擬似的に攻撃中にできる。
  実戦は `combat_manager.process_attack(AttackAction(...))` で set/clear まで通る。
- 参照実装: `dm26-rp2.C.71/77`、`tests/ut/test_dm26_rp2_c71_77.py`。

## フィールド / D2フィールド

- `kind: "field"`（`"フィールド"`）は `cards/field_card.py` の `FieldCard` を生成する。
  クロスギアのジェネレートと同型で、手札から `UseCardAction`（`use`）でバトルゾーンへ
  「展開」する単独エレメント。展開時は横向き＝アンタップ（`tapped=False`）。CLI では
  向きは無関係。
- バトルゾーンを離れる際に `CardMover` が `card.reset_battle_state()` を呼ぶため、
  バトルゾーンに出るカードクラスには必ず `reset_battle_state` を実装すること
  （未実装だと破壊・移動時に `AttributeError`）。
- **D2フィールド**は `special_types: ["d2"]`。`is_d2_field(card)`（`cards/field_card.py`）で
  判定。「お互いの場に合計1枚」の状況起因処理は **展開（プレイ）時のみ** 発火する。
  `FieldCard.use` が成功時に `state_based_actions.note_d2_field_deployed(self)` で武装し、
  `StateBasedActions._apply_d2_field_supersede` が**1度だけ**、新展開の1枚を除く全D2を
  `DestroyMultipleAction`（置換適用バッチ）で破壊する。退化など展開以外の場登場では
  `use` を通らないため発火しない（＝置換で残す・退化で2枚共存が可能）。
- メインステップは `action_processor.process` 直後に `game_loop.resolve()` を呼ぶので
  実プレイでは展開→破壊が走る。**ハーネスの `summon`/`resolve_all_effects` は SBA を
  回さない**ため、テストでは `harness.game.game_loop.resolve()` を明示的に呼ぶ。

## `select_then` 効果の移動先ゾーン（`move_card`）

`select_then`（`SelectThenEffect`）の `effect.effect_id: "move_card"` は、
`effect` 内の `from_zone` / `to_zone` を尊重する。

```json
{
  "candidates": "opponent_battle_zone",
  "filter": { "card_type": "creature" },
  "effect": {
    "from_zone": "battle_zone",
    "to_zone": "mana",
    "reason": "...",
    "effect_id": "move_card"
  },
  "optional": true,
  "prompt": "...",
  "effect_id": "select_then"
}
```

- `to_zone` を省略すると `shield`、`from_zone` を省略すると `battle` がデフォルト。
- `to_zone: "shield"` のときだけシールド固有の処理（`shield_placement` による
  スタック先選択 / `face_options` による表裏選択）が走る。マナや墓地などへの
  移動では単純な `card_mover.move` になる。
- ゾーン名は `effects/zones/zone_effect_utils.py` の `ZONE_ALIASES` に従う
  （`battle` / `battle_zone`、`mana` / `mana_zone`、`shield` / `shields` / `shield_zone`、
  `grave` / `graveyard`、`deck`、`hand`）。
- 既存カードからのコピー流用に注意。シールド送りカード（例: uc28 Gal Keen）の
  `effect` ブロックをそのまま使うと `to_zone` が `shield` のままになり、
  「マナに置く」カードが誤ってシールドへ送られる。

## 「自分のクリーチャーの数」を参照する ref

バトルゾーンのクリーチャー数は `{"ref": "controller.creature_count"}` で参照する
（`opponent.creature_count` も可）。`RefResolver._part_creature_count` が
`game.query.get_creatures(controller=...)` を使って数える。

```json
"filter": {
  "card_type": "creature",
  "cost": { "lte": { "ref": "controller.creature_count" } }
}
```

- `controller.zone_count.<zone>` は **ゾーン名** を取る（`mana` / `battle` など）。
  `zone_count` の引数は `parse_zone` に渡されるため、`zone_count.creature` のように
  カード種別を渡すと `Unknown zone: creature` で実行時例外になる。
  「クリーチャーの数」が欲しい場合は `creature_count` を使うこと
  （`zone_count.battle` はエレメント等の非クリーチャーも数えてしまう）。
- 「マナゾーンの枚数」は `controller.zone_count.mana` /
  `opponent.zone_count.mana` と書く。`opponent.mana_zone_count` のような
  `<zone>_count` 連結形は **存在せず**、`RefResolver` が
  `ValueError: Unknown ref path` を投げて `select_then` の候補列挙ごと落ちる。
  ロードは通るが解決時に初めて例外化するため、ユニットテストで実際に
  対象が選べることを確認する。
- ref は filter 解決時（候補列挙時）に遅延評価される。`select_then` の前段で
  マナ踏み倒し等によりクリーチャー数が増減する場合、その結果が反映された数で
  判定される。

## filter の `card_type` のタイプミスに注意

`card_type` の値（`creature` / `spell` / `element` など）が誤っていると
（例: `cleature`）、フィルタは常に不一致となり候補が空になる。
能力が「何も起きない」挙動になるだけでロードエラーにはならないため、
ユニットテストで実際に対象が選べることを確認する。

## `trigger` キーの複合（DSL）表現

1 つの誘発能力を**複数の異なるイベント**から発火させたい場合
（例:「表向きでシールドに置かれた時、**または**自分のターンのはじめに」）、
`trigger` キーに `or` / `and` / `not` の複合トリガーを書ける。

```json
"trigger": {
  "type": "or",
  "triggers": [
    { "type": "zone_change", "card": { "ref": "source" }, "to_zone": "shield" },
    { "type": "turn_start", "player": "self" }
  ]
}
```

- `type`: `or`（いずれか一致で発火）/ `and`（全一致）/ `not`（不一致で発火）。
- サブトリガーは `triggers`（`conditions` / `any` / `all` も可）に配列で、
  `not` は `trigger`（または `condition`）に単一で書く。入れ子も可能。
- 能力は **全サブトリガーのイベント型**を購読する（上記なら `ZoneChangeEvent`
  と `TurnStartEvent`）。各リーフは自分が宣言したイベント型以外を自動で弾くので、
  「自分のカードがマナに置かれた zone_change」で `turn_start` リーフが誤発火する
  ことはない（`abilities/v2/trigger_matcher.py` の `_event_matches_type`）。
- 実装は `abilities/v2/spec_schema.py`（`is_composite_trigger` /
  `composite_sub_triggers`）、`trigger_matcher.py`（`event_types` / `matches` の
  複合分岐）、`card_db/v2_ability_parser.py`（`_validate_composite_event_spec`）。
- **リーフトリガーで使えるキーは限定**（`type`/`event`/`subject`/`attacker`/
  `player`/`card`/`filter`/`from_zone`/`to_zone`/`reason`）。`state` のような
  未対応キーはバリデーションで弾かれる。表裏など状態での絞り込みは `trigger`
  ではなく `active_if`（`card_state` で `shield_face_up` を判定）で行う。

## マナゾーンへの手動配置（テスト）

`CardTestHarness` には `put_mana` ヘルパーが無い。手動で配置する際は
**先に `card.owner` を設定**してから zone と `mana_zone.add` を行う。

```python
card.owner = player
card.zone = ZoneType.MANA
player.mana_zone.add(card)
```

## 条件は「トリガー時」と「解決時」のどちらで評価されるか

誘発能力の `active_if` / `condition` は **トリガー発火時**（イベント発生時、
`JsonTriggeredAbility._matches`）に評価される。`active_if` に「自分のクリーチャー
の数が相手より多ければ」のような**盤面に依存する条件**を書くと、トリガー時点の
盤面で判定され、効果解決時に状況が変わっても結果に反映されない。

「ターンの終わりに、（解決時に）クリーチャーが多ければ引く」のように
**解決時の盤面で判定**したい場合は、条件を `active_if` ではなく効果側の
`type: "if"`（`V2IfEffect`）に入れる。`if` 効果は解決時に `ConditionEvaluator`
で `condition` を評価し、真なら `then`、偽なら `else` の効果列を解決する。

```json
"effects": [
  {
    "type": "if",
    "condition": {
      "type": "card_count_matches",
      "from": { "player": "controller", "zone": "battle" },
      "filter": { "card_type": "creature" },
      "op": "gt",
      "value": { "ref": "opponent.creature_count" }
    },
    "then": [
      { "effect_id": "draw", "amount": 1, "max_amount": 1, "prompt": "..." }
    ]
  }
]
```

- `if` 効果は `EffectFactory`（`effects/effect_factory.py`）が **`type` キー**で
  ディスパッチする。`"effect_id": "if"` と書くと `effects/registry.py` 側へ回り
  `Unknown effect id: if` で落ちる。**必ず `"type": "if"`** と書く。
  一方 `then`/`else` 内の `draw` 等は従来どおり `effect_id` でよい。
- `active_zones`（例: `["shield"]`）と `active_if` の `shield_face_up` 判定は
  トリガー時のゲートとして残してよい（G城が表向きでシールドにある時だけ誘発）。
  盤面カウントだけを `if` に移すのがポイント。

## クリーチャー数の比較条件（`card_count_matches`）

「自分のクリーチャーが相手より多い」は条件型 **`card_count_matches`** で書く。
型名は `card_count` ではない（`card_count` は未登録で `Unknown condition type`）。
比較演算子は `op`（`eq`/`ne`/`lt`/`lte`/`gt`/`gte`、記号 `>` 等のエイリアスも可）、
基準値は `value`（`{"ref": "opponent.creature_count"}` などの ref 可）。

```json
{
  "type": "card_count_matches",
  "from": { "player": "controller", "zone": "battle" },
  "filter": { "card_type": "creature" },
  "op": "gt",
  "value": { "ref": "opponent.creature_count" }
}
```

- 対象カード集合は `from: {player, zone}`（または `cards: {ref}`）で指定し、
  `filter` で絞る。`zone: "creature"` のような種別名は `parse_zone` で落ちるので
  **`zone: "battle"` + `filter.card_type: "creature"`** とする。
- 数えるのは「条件が満たすべき値」との比較。`controller`/`opponent` の
  `creature_count` ref（`RefResolver._part_creature_count` →
  `query.get_creatures`）と組み合わせると左右が同じ数え方になり整合する。

## 「1枚引いてもよい」（任意ドロー）の書き方

`DrawEffect` 自体に `optional` は無い。「引いてもよい」は **`max_amount`** を使い、
プレイヤーに 0〜N 枚の枚数選択をさせて表現する（`min_amount` 既定 0）。

```json
{ "effect_id": "draw", "amount": 1, "max_amount": 1, "prompt": "カードを1枚引きますか？" }
```

`resolve_effect_amount`（`effects/amount_choice.py`）が 0/1 の選択を取り、0 なら
引かない。能力レベルの `optional` フラグは `JsonTriggeredAbility` では誘発の
可否プロンプトに**配線されていない**ので、任意ドローには使えない。

## 自分以外のクリーチャーの召喚コストを軽減する（グローバル cost_modifier）

`Card.get_current_cost` の `modify_cost` 走査は **召喚するカード自身の能力のみ**を
見る。G城などが「自分のクリーチャー（＝他のカード）の召喚コストを軽減する」
継続効果は、v2 静的能力 `type: "cost_modifier"` で記述し、
`SummonCostReductionAbility`（`abilities/traits/`）として実体化する。

```json
{
  "type": "cost_modifier",
  "applies_to": { "player": "controller", "filter": { "card_type": "creature" } },
  "modifier": { "amount": -1, "min_cost": 1, "per_turn": 1, "optional": true },
  "condition": { "type": "card_state", "card": "source", "state": "shield_face_up", "value": true },
  "ability_id": "<card>_cost_reduction"
}
```

- 仕組み: `Card.get_current_cost(player, game)` が `core/cost_modifiers.py` の
  `apply_global_summon_cost_modifiers` を呼び、player のシールド／バトルゾーンの
  カードが持つ `modify_summon_cost` を走査して反映する。`game` が無い呼び出し
  （表示用など）では軽減は適用されない。
- **支払い可否のパスにも `game` を通すこと**。`Player.can_play(card, game)` /
  `_play_cost(card, game)` が `game` を受け取り、`ActionValidator`（`self.context`）と
  `SummonActionHandler`（`self.game_controller`）から渡す。ここを通さないと、
  軽減後なら支払えるのに**全額で支払い不能と判定**され召喚が弾かれる。
- `per_turn`（「各ターンに1度」）の使用回数は **召喚確定時に1度だけ** 消費する。
  コスト計算・支払い可否（`can_play`）では `consume=False`／`interactive=False`
  で呼び、実際の召喚時に `SummonActionHandler` が
  `get_current_cost(..., consume=True, interactive=True)` を **一度だけ** 呼ぶ。
  下限（`min_cost`、既定1＝「0以下にならない」）に張り付き軽減が無意味な場合は
  消費しない（任意なので適用しない扱い）。
- **「してもよい」軽減の CLI 選択**: `modifier.optional: true` のとき、実際の
  召喚時（`interactive=True`）に `game.choice_manager.select` で
  「コストを少なくする／そのまま支払う」を尋ねる。`interactive=False`（候補列挙・
  支払い可否・表示用）では尋ねず、有利なので適用済みとして扱う（毎回プロンプト
  しないため）。`can_play` は軽減後（＝最良ケース）で可否判定するので、採用時は
  必ず支払える＝確定前 consume でも `tap_mana` は失敗しない。辞退して全額が
  払えない場合のみ召喚が中止されるが、その場合は何も消費しない。テストでは
  `ScriptedChoiceManager.when_prompt_contains("少なくしますか", ...)` で選択を固定。
- `applies_to.card == "self"`（自己コスト修飾）の `cost_modifier` は従来どおり
  未配線の `StaticAbility` プレースホルダのままにしている
  （`V2AbilityFactory._is_summon_cost_reduction` で振り分け）。
- DM26-RP1 の構造化能力は **全 spec に `ability_id` キー必須**
  （`tests/card_db_tests/test_dm26_rp1_v2_authoring.py`）。`cost_modifier` 静的にも
  忘れず付ける。

## G・城（城/ギャラクシー）の誘発能力はシールドゾーンで動かす

城（`kind: "castle"`、ギャラクシーは `special_types: ["galaxy"]`）は**シールドゾーン**に
表向きで置かれて機能する（`cards/castle_card.py`）。一方、`JsonTriggeredAbility` の
`active_zones` 既定は空＝`TriggeredAbility.can_trigger` で `[BATTLE]` にフォールバック
するため、**`active_zones` を書かないと誘発が一切発火しない**（バトルゾーン前提に
なる）。城の誘発は必ず次を付ける:

```json
"active_zones": ["shield"],
"active_if": { "type": "card_state", "card": "source", "state": "shield_face_up", "value": true }
```

- `active_zones`（領域）と `active_if`（表向き＝アクティブ状態）は別物。両方必要。
- 領域をまたいで発火させたい誘発（「このG城が離れた時」など）は `active_zones: "any"`。
- 参照実装: `dm26-rp1.VR.1/77`（Evolution Saga, The La Moon）、`dm26-rp1.R.25/77`。

## 「カードを引いた時」の誘発は `zone_change` で書く（`draw` イベントは無い）

v2 のイベント表（`abilities/v2/event_map.py`）に `draw` は**存在しない**。
`type: "draw"` を `trigger` に書くと `Unknown v2 trigger event: draw` でカード自体が
ロード不能になる。ドローは「山札→手札」の領域移動なので `zone_change` で表現する:

```json
"trigger": {
  "type": "zone_change",
  "player": "controller",
  "from_zone": "deck",
  "to_zone": "hand",
  "reason": { "in": ["draw", "replacement_draw"] }
}
```

- `reason` は通常ドローが `"draw"`（`core/player.py`）、置換ドローが
  `"replacement_draw"`。両方拾うなら `{ "in": [...] }`（`core/dsl_compare.py` の
  `in` 演算子）。`reason` を絞らないと「山札サーチで手札に加える」等も拾う。
- 「自分のターンに」は `condition: { "type": "turn_player_is", "player": "controller" }`
  を併用する（ドロー自体は相手ターンにも起こり得るため）。

## 「相手は自身の手札を1枚選び、捨てる」は `discard` の `target_player`

`discard` 効果（`effects/zones/discard_effect.py`）は **`player`＝手札の持ち主かつ
選択者**。相手に捨てさせるには `target_player: "opponent"` を付ける（`resolve_player`
で相手に解決し、選択も相手が行う）。`move_card` で `target_player: opponent` にすると
**選択者は自分のまま**になり「自分が相手の手札を選ぶ」別の意味になるので使い分ける。

```json
{ "effect_id": "discard", "amount": 1, "optional": false, "target_player": "opponent" }
```

## 「各ターンはじめて」は `active_if` と独立に消費される（最初の攻撃で確定）

`first_time_each_turn`（`condition`）は、**トリガーとなったイベント**（例: そのターン
最初の攻撃）に紐づくカウンターで、`active_if`（城が表向き＝アクティブ）とは独立に
評価・消費する。`JsonTriggeredAbility._matches` は `condition` と `active_if` を
**両方とも必ず評価**してから AND を取る（`active_if` で短絡しない）。

- これにより、城が**非アクティブな間に最初の攻撃**が起きてもカウンターが消費され、
  その後アクティブ化しても**次の攻撃では発動しない**（DMのルール通り）。
- もし `active_if` で短絡すると、最初の攻撃でカウンターが消費されず、後からアクティブ
  化した2回目の攻撃で誤発動する（修正前の挙動）。
- 現状 `first_time_each_turn`/`once_per_turn` を `active_if` と併用するのは城のみ
  （`dm26-rp1.VR.1/77`・`R.25/77`）。`once_per_turn`（能力の使用回数）でこの順序が
  問題になるケースが出たら、消費を `active_if` ゲートの内側に置く設計を再検討する。
- 検証例: `tests/ut/test_dm26_rp1_r25_77.py::
  test_reactivation_after_first_attack_does_not_react_to_next_attack`。

## クリーチャーを発生源にした自分シールドのブレイク（`creature_break_shield`）

「そのクリーチャーが自分の（他の）シールドをブレイクする」は汎用化した
`creature_break_shield`（`effects/zones/break_shield_effect.py` の
`BreakShieldEffect` に `breaker`/`exclude`/`prompt` を追加して配線）で書く。
通常の `break_shield` はブレイク発生源が常に `source_card`（城など）になるため、
**クリーチャーを発生源にしたい場合はこちらを使う**。

```json
{
  "effect_id": "creature_break_shield",
  "breaker": { "ref": "event.card" },
  "amount": 1,
  "target": "own_shields",
  "exclude": { "ref": "source" },
  "optional": true,
  "prompt": "Choose one of your other shields to break",
  "connector": "then"
}
```

- `breaker`（ref）: ShieldBreakEvent の発生源になるカード。未指定なら `source_card`。
- `exclude`（ref）: 候補から外すカード。**G城（ギャラクシー）は自分専用スロットに
  入り `is_fortified_castle=False` のため `visible_shields()` に自分自身が盾として
  現れる**（`zones/shield_zone.py`）。「自分の**他の**シールド」を割らせるには
  `exclude: { ref: "source" }` で城自身を除外する（無いと城が候補に混じる）。
- 城を要塞化した（`is_fortified_castle=True`）盾は `visible_shields()` から除かれる
  ので、その場合は除外不要。今回の城は `play_galaxy_castle` で要塞化しない。

## 「ブレイクしたら〜」「各ターンに1度（実行時だけ消費）」は gate/mark + `then`

「もよい」で**実際に実行したときだけ**後続や各ターン1度を消費したい連鎖は、
`once_per_turn_gate` → 本処理(optional) → `once_per_turn_mark` → 後続、をすべて
`connector: "then"` で繋ぐ（`PackagedEffect` は直前効果が attempted=False だと
`then` 後続を止める。`effects/composition/once_per_turn_effect.py` 参照）。

- gate(`consume=False`): 未使用なら True、使用済みなら False で後続停止。
- 本処理が optional でスキップ/対象不在なら attempted=False → mark に到達せず
  **各ターン1度は消費されない**（断れば同ターンの次のクリーチャーで再挑戦できる）。
- mark(`consume=True`): ここまで来た（＝実行できた）ときだけターンマーカーを書く。

## 一時的なキーワード付与は `temporary_ability` の `ability`（`keyword` ではない）

「このターン、スピードアタッカーを与える」は `temporary_ability` で付与する。
registry は `ability=spec["ability"]` を読み `dict(ability)` するので、必ず
**`"ability": { "id": "speed_attacker" }`（dict）**で渡す（`"keyword": "..."` や
文字列だと未配線/`dict()`失敗）。付与は実際に `card.abilities` へ追加されるため、
`card.has_ability(SpeedAttackerAbility)` で参照可能（`core/validator/
attack_validator.py` がこの形で判定）。`until_end_of_turn` で自動的に外れる。

- 「自分のクリーチャー1体に与える」は対象選択。v2 `select`(`candidates:
  "own_creatures"`, `store_as`) で選ばせ、`temporary_ability` の `target:
  { ref: "<store_as>" }` で受け取る（`effects/effect_factory.py` の V2SelectEffect）。
- 参照実装: `dm26-rp1.R.26/77`、`tests/ut/test_dm26_rp1_r26_77.py`。

## 「各ターン1度、別ゾーンから召喚してよい（コストは支払う）。そうしたら〜」

「常在型で別ゾーンからの召喚を許可し、実際に召喚したら後続を行う」は
`summon_rule` → `play_from_zone`（`abilities/traits/play_from_zone_ability.py`）の
**プレイ許可（play permission）** で組む。新規 Python は最小限で、汎用の `move`
効果などをそのまま合成する。

```json
{
  "type": "summon_rule",
  "ability_id": "<card>_summon_from_mana",
  "rule": {
    "kind": "from_mana",          // = play_from_zone（zones は明示する）
    "zones": ["mana"],
    "card_types": ["creature"],
    "active_zone": "shield",       // 城はシールドゾーンで発動
    "per_turn": 1,                 // 「各ターン1度」（実召喚時のみ消費）
    "follow_up": [ { "type": "move", "from_zone": "deck", "to_zone": "mana",
                     "selection": "top", "amount": 1, "tapped": true,
                     "optional": true, "prompt": "…" } ]
  }
}
```

- 仕組み: `get_play_actions`/`can_use_for` がメインステップの合法手として
  `SummonAction(play_permission=self)` を出す。実際に召喚が成立すると summon
  handler が **`mark_used()`** を呼ぶ（`core/action_handlers/summon_action_handler.py`）。
  `PlayFromZoneAbility.mark_used` で `per_turn` を消費し、**`follow_up` を
  `EffectFactory` で組んで `effect_resolver.add_effect` でキューへ積む**
  （召喚解決後の通常ループで解決＝「そうしたら」）。
- `active_zone: "shield"` は城が**表向き**の間だけアクティブ（`_is_active` が
  `shield_face_up` を確認）。`per_turn` は実召喚時だけ消費するので、許可を
  使わなければ消えない。
- コストは通常どおり支払う（`ignore_cost` にしない）。テストでは召喚されるマナの
  クリーチャーとは別に、支払い用のアンタップ・マナを用意する（自分自身は
  pending で抜けるため別の untapped mana が要る）。
- 参照実装: `dm26-rp1.R.27/77`、`tests/ut/test_dm26_rp1_r27_77.py`。

## G城から「自分のクリーチャーすべて」へ能力を付与する（`grant_rule` + `active_zone`）

`grant_rule`（ScopedGrantAbility）は既定で**付与元がバトルゾーンにある間だけ**
機能する。G城のように**シールドゾーンから**全体へ付与する場合は、`rule` に
`active_zone: "shield"` を指定する（SBA の付与元スキャンもシールドゾーンを
見る）。表向き条件は `condition`（`card_state` の `shield_face_up`）に書けば、
hyper_mode 以外の dict 条件はそのまま `active_if` として渡され、
`active_if_matches` → `ConditionEvaluator` で評価される。

```json
{
  "type": "grant_rule",
  "ability_id": "<card>_power_aura",
  "rule": {
    "scope": "own_creatures",
    "active_zone": "shield",
    "ability": {
      "id": "power_buff",
      "amount": 2000,
      "active_if": { "type": "turn_player_is", "player": "opponent" }
    }
  },
  "condition": { "type": "card_state", "card": "source",
                 "state": "shield_face_up", "value": true }
}
```

- 「相手のターン中、パワー+2000」のような**条件付き定数パワー修正**は、
  汎用能力 **`power_buff`**（`abilities/auras/power_buff_ability.py`）を付与する。
  `active_if` はパワー参照のたびに評価されるため、ターンが変わるだけで
  SBA を回さなくても効果が切り替わる（付与自体の増減には SBA が必要）。
- 参照実装: `dm26-rp1.UC.31/77`、`tests/ut/test_dm26_rp1_uc31_77.py`。

## 「かわりにカードをN枚引く」ドロー置換（replacement の `draw` アクション）

「自分がカードを引く時、かわりに2枚引いてもよい」は v2 replacement で書く。
`replace_with.effects` に通常の `draw` 効果を入れると**置換が再帰して無限ループ**
になるため、専用の置換アクション **`{"type": "draw", "amount": N}`** を使う
（`JsonReplacementAbility._draw_replace_action` が置換を経由しない
`reason: "replacement_draw"` のドローを行う）。

```json
{
  "ability_id": "<card>_draw_replacement",
  "type": "zone_change",
  "active_if": { "type": "source_has_state", "state": "hyper_mode" },
  "attempt": { "event": "zone_change_attempt", "from_zone": "deck", "to_zone": "hand" },
  "condition": { "type": "event_zone_change_matches", "player": "controller", "reason": "draw" },
  "optional": true,
  "prompt": "かわりにカードを2枚引きますか？",
  "replace_with": { "cancel_event": true, "actions": [ { "type": "draw", "amount": 2 } ] }
}
```

- `attempt` には `reason` / `player` キーが**無い**。「自分の」「通常ドローのみ」の
  絞り込みは `condition` の **`event_zone_change_matches`**（`player` と `reason` を
  サポート）で行う。`reason: "draw"` に絞ることで、置換ドローやサーチによる
  手札追加には再適用されない。
- 複数枚ドロー（`draw(2)` など）は**1枚ごとに**置換判定される（2枚→4枚）。
- 新しい置換アクションを足したら `card_db/card_definition_validator.py` の
  `REPLACE_ACTION_VALIDATORS` にも登録する（忘れると validate で
  `unknown replacement action` になる）。
- 参照実装: `dm26-rp1.UC.34/77`、`tests/ut/test_dm26_rp1_uc34_77.py`。

## 「このシールドの下に置く」は v2 `move` の `stack_on`（ref）で固定する

シールドゾーンへの移動で**重ね先スロットを ref で固定**できる
（`V2MoveEffect._shield_stack_on`）。`shield_placement: "stack"` はプレイヤーが
スロットを選ぶ方式なので、「**この**シールドの下」のように発生源の城のスロットへ
固定したい場合は `stack_on: {"ref": "source"}` を使う。

```json
{
  "type": "move",
  "card": { "ref": "event.card" },
  "from_zone": "graveyard",
  "to_zone": "shield",
  "stack_on": { "ref": "source" },
  "optional": true,
  "prompt": "..."
}
```

- `stack_on` 指定時は新しいシールドは増えず、既存スロットに積まれる
  （`shield_zone.add(card, stack_on=...)`）。スロットの主（城など）がシールド
  ゾーンに無ければ移動しない。
- v2 `move` はシールド行きで `shield_face_up` を渡さないため**裏向き**になる
  （「裏向きでこのシールドの下に置く」に合致）。
- `from_zone` を明示した v2 `move` は、解決時にカードがその領域を**既に離れて
  いたら何もしない**（「破壊された時、そのクリーチャーを墓地から〜」で、解決前に
  墓地から動いたケースの暴発防止）。
- 参照実装: `dm26-rp1.UC.31/77` の破壊誘発。

## 「ブロッカーを持つクリーチャー」は filter の `has_keyword`

filter DSL の **`has_keyword`** は、カードの能力のうち `ability_id` が一致する
ものを探す（registry 経由で生成された能力は `_attach_metadata` で `ability_id`
が付く）。「自分の『ブロッカー』を持つクリーチャーの召喚コストを1少なくする」は
`cost_modifier` と組み合わせて新規 Python なしで書ける。

```json
"applies_to": {
  "player": "controller",
  "filter": { "card_type": "creature", "has_keyword": "blocker" }
}
```

- 参照実装: `dm26-rp1.UC.35/77`、`tests/ut/test_dm26_rp1_uc35_77.py`。

## 「攻撃もブロックもできない」一時ロックは `select_then` + `temporary_combat_restriction`

「相手のクリーチャーを1体選ぶ。次の自分のターンのはじめまで、攻撃もブロックも
できない」は既存パーツの合成で書ける。`select_then` は `effect_id:
"temporary_combat_restriction"` を特別扱いし、選んだ対象へ
`TemporaryCombatRestrictionEffect` を直接適用する。

```json
{
  "effect_id": "select_then",
  "candidates": "opponent_creatures",
  "optional": false,
  "prompt": "...",
  "effect": {
    "effect_id": "temporary_combat_restriction",
    "restrictions": ["attack", "block"],
    "duration": "until_start_of_controller_turn"
  }
}
```

- `restrictions` は `"attack"` / `"block"` の配列。攻撃禁止は
  `AttackValidator._is_attack_prevented`、ブロック禁止は blocker 列挙側が
  `prevents_block()` を見る。
- 「次の自分のターンのはじめまで」は `duration: "until_start_of_controller_turn"`。
- 参照実装: `dm26-rp1.UC.35/77`（置かれた時＋各ターンはじめての攻撃の2誘発、
  攻撃側は R.25 と同じ `first_time_each_turn` パターン）。

## v2 `battle` 効果（指定した2体をバトルさせる）と `enter_battle` の `from_zone`

- 「相手のクリーチャーを1体選ぶ。その2体をバトルさせる」は v2 `battle` 効果
  （`effects/effect_factory.py` の `V2BattleEffect`）で書く。`battle_two_creatures`
  は**両方を任意選択**する別物。攻撃側／防御側を ref で固定したいときは `battle`：

  ```json
  { "type": "battle", "connector": "then",
    "attacker": { "ref": "event.card" },        // 出たクリーチャー（誘発の主体）
    "defender": { "ref": "creature_to_battle" } } // 直前の select の store_as
  ```

  - **攻撃側に `{ ref: "source" }` を使わない**こと。`source` は能力の発生源
    （＝城など）に解決される。出たクリーチャーは **`event.card`**（イベントの
    対象カード）で参照する（`core/ref_resolver.py`）。
  - 防御側が未解決（任意 select をスキップ）なら何もしない。`connector: "then"`
    で select 成立時のみ実行されるようにする。
- **`enter_battle` トリガーの `from_zone` は正規ゾーン名で書く**：`"mana"`・
  `"battle"`・`"deck"` 等。`"mana_zone"` のような別名は不可。trigger matcher は
  イベント側ゾーンを `parse_zone(...).name.lower()`（=`"mana"`）に正規化する一方、
  期待値は文字列のまま比較するため、`"mana_zone"` だと**永遠にマッチしない**
  （`abilities/v2/trigger_matcher.py` の `_match_zone_expression`）。


## バトルの流れとスレイヤー（バトルの後タイミング）

`CombatManager.process_battle` のバトルシーケンス（イベントは
`events/battle_event.py`、v2 名は `battle_declared` / `battle_start` /
`battle_won` / `battle_lost` / `battle_end`）:

1. `BattleDeclaredEvent` … バトル成立の宣言。置換効果を含む「バトル中」の
   常在型能力の開始点。
2. `BattleStartEvent` … 「バトルする時」の誘発をここで解決
   （`game_loop.resolve()`）。パワーパンプ等はバトル実行前に反映される。
3. 誘発解決後に両者がバトルゾーンに残っていなければ**バトル不成立**
   （勝敗イベントも「バトルの後」も発生しない）。
4. パワー比較 → `BattleWonEvent` / `BattleLostEvent`（**同パワーは両者敗北**＝
   `BattleLostEvent` が両者に発生し `BattleWonEvent` は出ない）→ 敗者破壊と
   誘発の解決。
5. **スレイヤーによる破壊**（バトルの後）→ `BattleEndEvent`。

- **スレイヤーはマーカー能力**（`abilities/keywords/slayer_ability.py`、
  keyword id `slayer`）。CombatManager が `BattleStartEvent` 解決後の時点で
  `has_ability(SlayerAbility)` を捕捉し、バトルの後に相手がまだバトルゾーンに
  いれば破壊する。**自身がバトルで破壊されていても発動する**（捕捉済みのため）。
  勝った場合は相手が既に墓地なので二重破壊しない。
- 「このターン、スレイヤーを与える」は `temporary_ability` の
  `"ability": { "id": "slayer" }` で付与する（speed_attacker と同型）。
- `process_battle` は内部で `game_loop.resolve()` を呼ぶため、**バトル誘発の
  効果はバトルの後タイミングまでに解決済み**になる。テストで
  「process_battle 直後にキューに効果が残っている」ことを当てにしない
  （結果の状態で検証する）。
- 参照実装: `dm26-rp1.UC.37/77`、`tests/ut/test_dm26_rp1_uc37_77.py`、
  `tests/ability_tests/test_slayer_and_battle_flow.py`。

## 「このターン、そのクリーチャーが破壊された時〜」残存効果は temporary_ability で triggered を付与

「このターン、そのクリーチャーが破壊された時、カードを2枚引く」のような
残存効果は、対象クリーチャーへ **`temporary_ability` で registry の
`triggered`（GenericTriggeredAbility）を一時付与**して書ける。

```json
{
  "effect_id": "temporary_ability",
  "ability": {
    "id": "triggered",
    "event": "destroy",
    "condition": "self",
    "active_zones": "any",
    "ignore_source_continuity": true,
    "effects": [ { "effect_id": "draw", "amount": 2 } ]
  },
  "duration": "until_end_of_turn",
  "target": { "ref": "slayer_target" },
  "connector": "then"
}
```

- **`ignore_source_continuity: true` が必須**。`DestroyEvent` は墓地移動の
  **前**に発行され、その後の移動で `zone_change_counter` が進むため、
  既定のゴースト効果チェック（`CardSnapshot.is_same_card`）で
  「継続条件を満たさない」とスキップされる。自分自身の破壊に誘発する能力は
  これを無効化する。`active_zones: "any"` も併せて指定する。
- 付与先の誘発が購読されるのは付与時に `target.abilities_registered` が
  真の場合のみ（`TemporaryAbilityEffect._register_if_needed`）。テストで
  手動配置したクリーチャーは `register_abilities(event_manager)` を先に呼ぶ。

## 「選んだ1体に複数の効果」は select_then の effects リストで書く

「クリーチャーを1体選ぶ。このターン、パワー+6000し、相手プレイヤーを攻撃
できない」（dm26-rp1.UC.46/77）のように、**1回の選択で同じ対象へ複数の
状態変更**を適用する場合は、`select_then` に `effect`（単発）ではなく
`effects` リストを渡す。

```json
{
  "effect_id": "select_then",
  "candidates": "creatures",
  "optional": false,
  "prompt": "...",
  "effects": [
    { "effect_id": "modify_power", "amount": 6000, "duration": "end_of_turn" },
    { "effect_id": "temporary_combat_restriction",
      "restrictions": ["attack_player"], "duration": "end_of_turn" }
  ]
}
```

- 呪文のトップレベル `effects` は唱える処理中に同じ `package_context` を
  共有する。`gather_matching` / `select` + `store_as` で保存した結果は、
  後続の `for_each_stored` や `ref` から参照できる。
- `temporary_combat_restriction` の `restrictions` に `attack_player` を
  指定すると**プレイヤーへの攻撃だけ**を禁止する（`attack` は攻撃全体）。
  判定は `AttackValidator.can_attack_target`（対象がプレイヤーの場合）と
  `GameQuery.get_attack_targets`（候補列挙）の両方が見る。
- `modify_power` は `duration` 付きで `TimedPowerModifierEffect` になる。
  呪文発（trigger_snapshot なし）の場合は対象がバトルゾーンに居るかだけで
  継続判定する。
- 参照実装: `dm26-rp1.UC.46/77`、`tests/ut/test_dm26_rp1_uc46_77.py`。

## シールド・プラス、チャージャー、ブレイク置換の小パーツ

- `shield_plus` は `AddDeckToShieldEffect` のエイリアス。山札の上から
  `amount` 枚（既定1）を裏向きで既存シールド束に追加する。シールド枚数は
  `ShieldZone` のスロット数なので増えない。
- `charger` は呪文効果の末尾に置く。解決時に呪文自身へマーカーを立て、
  `CastSpellActionHandler` が墓地ではなくマナゾーンへ移動する。
- `shield_break_redirect` / `break_this_shield_instead` は
  `ShieldBreakAttemptEvent` の `shield_card` / `shield_cards` をこのシールドへ
  差し替え、`consume_remaining_breaks` で残りの複数ブレイクを消費する。
  このシールド自身が直接ブレイク対象の時も先に任意確認し、承諾なら通常の
  ブレイクとして手札へ、拒否なら後続のG城共通置換などに処理を渡す。
  G城のリダイレクト経由ブレイクは `reason: "shield_break"` の通常移動なので、
  G城共通の墓地置換は連鎖しない。
- 参照実装: `dm26-rp1.C.53/77`、`dm26-rp1.C.56/77`、
  `dm26-rp1.C.57/77`。

## 「相手のクリーチャーが出る時かわりにマナへ」は replacement の attempt + replace_with.to_zone

「相手のクリーチャーが召喚以外の方法で出る時、かわりにマナゾーンに置く」
（dm26-rp1.UC.47/77）は新規 Python 不要で、`attempt`（`to_zone: "battle"` +
`card_filter`）に `condition: event_zone_change_matches` の
`reason: {"ne": "summon"}` を組み合わせ、`replace_with.to_zone: "mana"` で
行き先を差し替える。

- **バトルゾーンへ移動中のカードは pending 状態**になる。
  `ReplacementAttemptMatcher._match_card_filter` は評価の間だけ pending を
  外して判定する（`CardFilterEvaluator` は pending を一律除外するため）。
  attempt の `card_filter` が効かない時はまずこれを疑う。
- G城の「表向きの間だけ」は `active_if: { type: "card_state", card:
  "source", state: "shield_face_up", value: true }` で書ける
  （replacement は全ゾーンから収集されるため active_if での門番が必須）。
- 参照実装: `dm26-rp1.UC.47/77`、`tests/ut/test_dm26_rp1_uc47_77.py`。

## 自己召喚コスト修飾と攻撃先誘導（DM26-RP1 UC.44 / UC.45）

- 「手札から召喚するなら、召喚コストを+N」は static の `cost_modifier` で
  `applies_to: { card: "self", from_zone: "hand" }` + `modifier: { amount: N }`。
  `SelfSummonCostModifierAbility` が `Card.get_current_cost` の
  `modify_cost` フックから呼ばれ、**カードの現在ゾーン**で適用可否を判定する
  （マナ召喚など他ゾーンからの実行では適用されない）。
- 「相手のクリーチャーが攻撃するなら、可能ならこのクリーチャーを攻撃する」は
  static の `attack_rule` + `rule.kind: "must_attack_this"`（→
  `AttackLureAbility`）。攻撃を**強制しない**（`opponent_attack_mandatory`
  とは別物）。誘導先が正規の攻撃対象にならない場合（アンタップ等）は
  制限しない。
- 参照実装: `tests/ut/test_dm26_rp1_uc44_77.py`、
  `tests/ut/test_dm26_rp1_uc45_77.py`。

## 日本語種族 filter と scope 付き一時付与（DM26-RP1 C.68 / C.69 / C.75）

- 日本語テキストの種族指定は `filter: { "race_ja": "..." }` を使う。
  `race_ja` は部分一致なので、`"ドラゴン"` が `"アーマード・ドラゴン"` に
  一致する。英語種族用の `race` / `races` フィルタは受け付けない。
- 種族指定セイバーは `keyword` に `{ "ability_id": "saber",
  "race_ja": "超化獣" }` と書く。
- `grant_rule` は `rule.filter` と `rule.exclude_source` を指定できる。
  「ドラゴンと他の超化獣へ付与」は `scope: "own_creatures"` +
  `filter: { "or": [{ "race_ja": "ドラゴン" }, { "race_ja": "超化獣" }] }` +
  `exclude_source: true`。
- `temporary_ability` は `scope` を指定すると、解決時点のスコープ内カードすべてへ
  一時能力を配る。`Invincible Tower` の全軍 `power_buff` / `t_breaker` のような
  呪文効果に使える。

## 「その後」と「そうしたら」の connector 規約（DM26-RP1 レビューで統一）

- effects 配列内の `connector` は **`"then"` = 直前の効果が実際に実行された
  場合のみ続行**（`PackagedEffect` が前の効果の attempted/解決結果を見る）。
  省略時（= `"after"`）は無条件に続行する。
- カードテキストとの対応:
  - 「**そうしたら**〜」（条件付き）→ `"connector": "then"` を付ける。
  - 「**その後**〜」（無条件）→ connector を付けない。
- 「N枚引いてもよい」は `optional: true` ではなく
  `{ "amount": N, "max_amount": N, "prompt": "..." }` で表現する。
  `draw` の builder は `optional` を読まないため、付けても強制ドローになる
  （サイレント無視）。「2枚引いてもよい。そうしたら捨てる」のような
  all-or-nothing は `type: "choice"` で分岐させる（ニバイケン参照）。
- `player_zone_count` 条件の `op` 省略時は **`eq`（完全一致）**。
  「N以上」は必ず `"op": "gte"` を明示する（ブライゼジェネレイド参照）。
- G城の「離れた時」誘発は `active_zones: "any"` +
  `condition: { "type": "event_zone_change_matches",
  "from_shield_face_up": true }` のパターンを使う（ジ・オリジナル/バルザーク/
  ブラック・エクスプロード参照）。`active_zones: ["shield"]` のままでは
  離れた後にゾーン判定が落ちて発火しない。
- `card_chosen` トリガーは `card: { "ref": "source" }` を必ず付ける。
  トリガーに何かフィールドがあると subject=self の既定照合がスキップされる
  ため、付け忘れると「相手が何かを選ぶたび」に誘発する（ボルシャック・
  メビウス参照）。

## 呪文の最上位 `effects` は registry 経由（`type:` 系 v2 effect は使えない）

`generic_spell.py` の `create_effects` は **`effects/registry.py` の `build_effects`**
（`effect_id` ベース）で呪文効果を組む。`EffectFactory` は通らないため、
呪文の**最上位** `effects` 配列に `type: "select"` / `type: "battle"` /
`type: "modify_power"` などの v2 effect を書くと `KeyError: 'id'` で実行時に落ちる
（ロード・validate は通るので要注意）。

- 呪文最上位で使えるのは registry に登録された `effect_id`（`select_then` /
  `move_card` / `draw` / `mill` / `gather_matching` / `choose_n_effects` 等）。
- `select` と `choose_number` は registry にブリッジ済み（`effects/registry.py` の
  `_select` / `_choose_number` が v2 `V2SelectEffect` / `V2ChooseNumberEffect` を生成）。
  なので `effect_id: "select"`（`store_as` で保存）・`effect_id: "choose_number"` は
  呪文最上位や `choose_n_effects` の各選択肢の `effects` 内でも使える。保存値は同じ
  package_context を共有するので、後続の registry effect が `{ "ref": ... }` で参照できる
  （例: `select` で選んだクリーチャーを `multiply_power` / `temporary_ability` の `target`
  に渡す。VR.11/77 の選択肢「パワー2倍＋パワード・ブレイカー付与」参照）。
- それ以外の v2 effect（`type: "move"` / `"destroy"` / `"battle"` /
  `"modify_power"` / `"if"` 等）は **triggered/activated 能力の `effects`**
  （`JsonTriggeredAbility` → `EffectFactory` 経由）や、`select_then` の
  **内部 `effects`** でのみ使える。
- 「選んだ対象へパワー修正」は呪文では `select_then` + 内部
  `{ "effect_id": "modify_power", "amount": N, "duration": "until_end_of_turn" }`
  で書く（`SelectThenEffect._resolve_modify_power`）。`select_then` の内部
  `effect_id: "battle"` は攻撃側を `effect_spec["target"]`（リテラルか `"self"`＝
  発生源）でしか取れず、**直前に選んだ別クリーチャーを ref で攻撃側にできない**。
  「自分のクリーチャー＋4000してその2体をバトル」（C72 FORBIDDEN RAGE）はこの
  制約で未実装（要 engine 拡張）。
- 参照実装: `dm26-rp2.C.67/77`・`dm26-rp2.C.62/77`（呪文 select_then）。

## マナ武装（特定文明のマナ N 枚以上で効果）= condition 能力語 `mana_armor`

「マナ武装」は **`mana_number`（マナの数字を変える別能力）とは無関係**。
`active_if` を取る**あらゆる能力・効果のゲート**として使える condition 能力語
**`{ "type": "mana_armor", ... }`** で書く。内部で `card_count_matches`
（マナゾーン＋文明フィルタ・gte）へ展開される（`core/condition_evaluator.py` の
`_evaluate_mana_armor`、登録は `core/condition_registry.py`）。パワー増加・
キーワード付与・誘発効果・置換など**どの能力にも同じ条件語**を書ける。

```json
"active_if": { "type": "mana_armor", "civilization": "light", "count": 3 }
```

- `civilization`（単一）/ `civilizations`（複数）、`count`（既定3）、
  `player`（既定 `controller`）。
- 参照テスト: `tests/ut/test_mana_armor_condition.py`。

「パワー+X し W・ブレイカーを与える」型（RP2 の多くのマナ武装）は次の2つを
同じ `active_if` で書く:

- **条件付きパワー強化**: 静的グループに `power_buff` を**生で**置けない
  （`V2AbilityFactory._static_to_registry_spec` が `type` 必須で、未知 type は
  `Unknown v2 static ability type` で例外）。`grant_rule` の **`scope: "self"`**
  で自身へ `power_buff`（`active_if: { "type": "mana_armor", ... }`）を付与する。
  `active_if` はパワー参照時に評価されるので、マナ枚数の増減は再 SBA 不要で反映。
- **条件付き W・ブレイカー付与**: keyword 配列に
  `{ "ability_id": "w_breaker", "active_if": { "type": "mana_armor", ... } }`
  を入れる（`_breaker` が `active_if` を `WBreakerAbility` に渡す）。
- 参照実装: `dm26-rp2.U.44/77`・`U.28/77`・`U.32/77`・`U.37/77`。
- ETB 等の選択効果（triggered）は v2 で書ける。「2体まで手札に戻す」は
  `type: "select"`(count 2, optional) + `type: "move"`(to_zone hand, cards ref)、
  「アンタップしている相手を破壊」は `filter: { "tapped": false }` + `type:
  "destroy"`。
- 参照実装: `dm26-rp2.U.44/77`（タップして出す＋攻撃誘導＋マナ武装）・
  `dm26-rp2.U.32/77`（ETB バウンス）・`dm26-rp2.U.37/77`（ETB 破壊）・
  `dm26-rp2.U.28/77`（ETB 2体タップ）。

## クリーチャーの「出た時または離れた時」誘発

クリーチャー自身の「出た時または離れた時」は `or` 複合トリガー＋
**`ignore_source_continuity: true` ＋ `active_zones: "any"`** で書く
（G城の uc49 と同型）。離れた後はバトルゾーンに居らず継続性チェックも
通らないため、この2つが無いと「離れた時」側が発火しない。

```json
"ignore_source_continuity": true,
"active_zones": "any",
"trigger": {
  "type": "or",
  "triggers": [
    { "type": "enter_battle", "card": { "ref": "source" } },
    { "type": "zone_change", "card": { "ref": "source" }, "from_zone": "battle" }
  ]
}
```

- 「1体選んでタップ＋次の自分のターンまでアンタップ阻止」は
  `select_then`(`effect: { "effect_id": "tap" }`, `store_as`) →
  `lock_untap`(`target: { "ref": ... }`, `duration:
  "until_start_of_controller_turn"`, `connector: "then"`)。
- 「1体選んで手札に戻してもよい」は `select_then`(`effect: { "effect_id":
  "bounce" }`, `optional: true`)。
- 参照実装: `dm26-rp2.U.48/77`（タップ＋アンタップ阻止）・
  `dm26-rp2.C.58/77`（任意バウンス）。

## マナ武装で未対応のもの（要 engine 拡張）

- 「パワーの合計がこのクリーチャーのパワー以下になるように破壊」（U.40 ガイグンシン）
  は `select_within_total_power` の `max_total_power` が **ref 非対応**
  （`SelectWithinTotalPowerEffect` が値を直接引き算する）。マナ武装で増減する
  自パワーを上限にできないため未実装。`max_total_power` の ref 解決を足せば対応可。

## 「自分の他のクリーチャーが出た時、永続バフ」（R.18 流星の使者 ウコン＆サコン）

別クリーチャーが出た時に **パワー+4000・SA・パワード・ブレイカーを恒常付与**する、
2つの新規部品を使う:

- **永続付与**: `temporary_ability` の `duration` に `"permanent"` を指定すると
  `DurationType.PERMANENT`（`has_duration_expired` が常に False）で期間終了しない。
  パワー増加は `ability: { "ability_id": "power_buff", "amount": 4000 }` を、SA/PB は
  `ability: { "id": "speed_attacker" }` / `{ "id": "powered_breaker" }` を grant。
- **「他の」= 自己除外**: enter_battle トリガーは `subject: "controller"` だと自分自身の
  登場でも誘発する。ability の `condition` に
  `{ "type": "not", "condition": { "type": "event_card_is", "card": "source" } }`
  を付けて発生源を除外する（`event_card_is` はイベントのカードが参照と同一かを判定）。
- 「各ターンに1度…してもよい」は `once_per_turn_gate` → v2 `choice`（与える/与えない）→
  `once_per_turn_mark`(`connector: "then"`)。choice で「与えない」を選ぶと空 effects で
  False を返し、`then` の mark に到達しないため消費されない。
- 参照実装: `dm26-rp2.R.18/77`。

## バトル中／ブロック中のパワー修整と「可能なら攻撃」（U.34/U.41/U.40 パラス・ガイグンシン）

パワーアタッカー（`current_attacker` を参照する常在型）を雛形に、戦闘状態を見る
常在型キーワードを追加した。`CombatManager` が `state` に参加者をセットする:

- `state.current_blocker` … ブロック宣言（`BlockDeclaredEvent` 発行直後の `try_block`）で
  セット、攻撃終了でクリア。**パワード・ブロッカー** `powered_blocker`(`amount`) が参照。
- `state.current_battle_attacker` / `current_battle_defender` … バトル成立
  （`BattleDeclaredEvent` 発行時）でセット、`BattleEndEvent` 後にクリア。攻撃・ブロック・
  「バトルさせる」強制バトルすべてを含む。**バトル中パワー** `battle_power`(`amount`) が参照。
- どちらも `effects/modifiers/battle_scoped_power_modifier_effect.py`（バトル終了で外れる
  一時修整）とは別アプローチ。常在型なので付与/解除のタイミング管理が不要。

「可能なら攻撃する」を特定クリーチャーへ一時付与するには `must_attack` キーワードを
`temporary_ability`（`duration: "until_start_of_controller_turn"` 等）で与える。
`ActionValidator._is_attack_required` は相手のカードだけでなく**攻撃クリーチャー自身の能力**も
走査するよう拡張済み（`MustAttackAbility.requires_attack` は持ち主＝攻撃者のとき True）。

`select_within_total_power` の `max_total_power` に `"source_power"` を渡すと、発生源の
現在パワー（マナ武装の +N 込み）を上限にできる（U.40 ガイグンシン「自分のパワー以下」）。
付与（grant_rule によるマナ武装）の反映は **SBA reconcile（ゲームループ）** 後に効くため、
テストで盤面直置きした場合は `game.game_loop.resolve()` を呼んでから検証する。

参照実装: `dm26-rp2.U.34/77`（パワード・ブロッカー＋q火 強制攻撃）・
`dm26-rp2.U.41/77`（バトル中+3000＋q光）・`dm26-rp2.U.40/77`（マナ武装＋自パワー以下破壊）。

## 「封印を付けて出す」(VR.6 メモッタ) — cip 抑止と特殊実装

《不明な不透明 メモッタ》の「封印を1つずつ付けて自分の墓地から出す」は**召喚ではない**特殊な
踏み倒し。封印されたクリーチャーは「無視される」ため、出した本人の「出た時」(cip) だけでなく、
**他カードの「自分のクリーチャーが出た時」等の登場誘発も発揮されない**。専用 effect
`revive_within_total_cost_sealed`
(`effects/composition/revive_within_total_cost_sealed_effect.py`) で実装した。

要点:
- バトルゾーンへ出す move で `publish_battle_enter=False` を指定し、`BattleZoneEnterEvent`
  （＝全ての「出た時」誘発の発生源）を発行しない。本リポジトリの「出た時」系トリガーはすべて
  `enter_battle`(BattleZoneEnterEvent) を購読しており、`zone_change` で battle 入場を見るカードは
  存在しないため、これで本人・他者の登場誘発をまとめて止められる。
- `publish_battle_enter` を抑止すると enter 時の `register_abilities` も走らないが、能力購読は
  ゲーム開始時（`setup_manager`）に全カードへ一括登録され以後解除されない設計なので、墓地由来の
  カードも購読済み。封印中は `is_ignored_by_seal` ガードで休止し解除後に働くため **手動登録は不要**。
  （テストハーネスは墓地へ直置きすると登録されないので、テスト側で `register_abilities` する。）
- 念のため出す直前に `card.is_ignored_by_seal = True` も立てる（`is_ignored_by_seal()` は
  zone==BATTLE のときだけ True なので墓地では無害）。`ZoneChangeEvent` 経由の本人誘発を
  `can_trigger` の seal ガードで休止させる安全側の措置。
- タップイン等の[状態定義効果]は `CardMover` の `ZoneChangeEvent`（`after_zone_change`）経由で
  自動適用されるため特別扱い不要。封印された状態のまま「タップして出る」(例: 相手 S6/S11
  ヴェノム・ランブルのハイパー時)。
- 実際の封印カードは move 完了後に `seal_manager.attach_seals` で付ける。山札切れ等で付けられ
  なかった場合は `is_ignored_by_seal` を戻して通常クリーチャー扱い。
- 旧実装（`summon_within_total_cost` で召喚扱いに出してから `for_each_stored` で
  `attach_seal`）は、封印前に cip が誘発してしまうため不可。

参照実装: `dm26-rp2.VR.6/77`、テスト `tests/ut/dm26_rp2/test_dm26_rp2_vr6_77.py`、
テスト用カード `tmp_cards/memotta_test_cards.json`。

## 超次元ゾーンとゼロ文明 (SR.S1/S11 ゾロ・ア・スタート)

《「業流」の頂 ゾロ・ア・スタート》で **超次元ゾーン**（`ZoneType.SUPER_DIMENSION`）と
**ゼロ文明** を追加した。

ゾーン:
- `ZoneType.SUPER_DIMENSION` を追加し、`Player.super_dimension`（`get_zone` のマッピングにも追加）と
  `effects/zones/zone_effect_utils.py` の `ZONE_ALIASES`（`super_dimension` / `hyperspatial`）に登録。
この効果は **置換効果** と **遅延誘発効果** の 2 つに分けて実装している（カード専用の
特別処理にしない）。
- 置換効果：`super_dimension_redirect`（`abilities/replacements/super_dimension_redirect_ability.py`）。
  `ZoneChangeAttemptEvent`（to=BATTLE, from≠SUPER_DIMENSION, 相手のクリーチャー, 相手のターン）を
  捕まえて `event.to_zone` を `SUPER_DIMENSION` へ差し替える。
- 遅延誘発効果：置換時に `SuperDimensionReleaseEffect`
  （`effects/zones/super_dimension_release_effect.py`）を生成し `resolve()` で `TurnStartEvent` を
  購読する。**ニンジャ・ストライクの山札戻し（`NinjaStrikeReturnEffect` が `TurnEndEvent` を購読）と
  同じ idiom**。対象プレイヤーの次のターン開始時に1度だけクリーチャーをバトルへ出して購読を解除する。
  対象と持ち主をクロージャで捕捉するため**発生源が離れても独立に解決**し、出す際は出たターン扱いで
  `summoning_sick = True` にする。

### ターンイベントの配信（重要）
`TurnStartEvent` / `TurnEndEvent` は `TurnManager` が `TurnTriggerResolver` 経由で**カードの
TriggeredAbility にのみ**解決していた。そのため `event_manager.subscribe` した購読者
（`TurnStatsManager` のターン集計リセット、`NinjaStrikeReturnEffect`、`SuperDimensionReleaseEffect`）は
本番のターン進行では発火しなかった（テストが手動 publish していただけ）。これを
`TurnManager._notify_non_triggered_subscribers(event_type, event)` で補い、ターンイベントを
**TriggeredAbility 以外の購読者**へも配信するよう統一した（カード能力は従来どおり
`TurnTriggerResolver` が処理するので二重発火しない）。これで遅延誘発効果はすべて同じ
「ターンイベントを購読する Effect」という形で書ける。

### registry 実装の置換能力を `replacement` グループへ
キーワードと同様、`attempt` を持たず `ability_id` だけ指定した置換能力は registry 実装へ
橋渡しされる（`v2_ability_factory._create_replacement_ability` / parser の `_validate_replacement`）。
`type` + `rule.kind` のブリッジを書かずに `{"ability_id": "super_dimension_redirect", "label": ...}` と
素直に書ける。

ゼロ文明:
- `Civilization.ZERO = 0`（無色）を追加し、`card_db/factory.py` の `CIVILIZATIONS` に `"zero"` を登録。
  ビット 0 なので文明の指定を持たず、召喚は文明を問わないマナのみで支払える（`is_multicolored` も False）。

エターナル・Ω:
- `eternal_omega`（`abilities/replacements/eternal_omega_ability.py`）はキーワード扱いの置換能力。
  自身がバトルゾーンを離れる移動（破壊 `DestroyAttemptEvent` / マナ・山札送り `ZoneChangeAttemptEvent`、
  ただし to が BATTLE / HAND を除く）で `event.to_zone` を `HAND` に差し替える。

参照: `dm26-rp2.SR.S1/S11`、テスト `tests/ut/dm26_rp2/test_dm26_rp2_s1_s11.py`。

### ソウルシフト（進化元コスト分の召喚軽減）
`soulshift`（`abilities/traits/soulshift_ability.py`、`ContinuousAbility.modify_cost`）は
**進化元のコスト分だけ自身の召喚コストを軽減**する（下限 `min_cost` 既定1）。
軽減量は「どの進化元を選んだか」に依存するため、`SummonActionHandler` は
**「召喚宣言 → 進化元選択 → マナ支払い → 出す」**の順で進化元を先に確定し、
選んだ進化元を `card._soulshift_source` に載せてから `can_play` / `get_current_cost` /
`tap_mana` を呼ぶ（`finally` で解除）。アクション生成・合法性判定・表示など**進化元が
未確定の段階**では、現在の進化元候補から最大の軽減になる組み合わせ（高コスト順に
`source_count` 体）を仮定する＝「軽減後なら払える」召喚を合法手として提示できる。
実支払いは進化元確定後に同じ `modify_cost` が選択済みの進化元で再計算する。
参照: `dm26-rp2.VR.1/77`、テスト `tests/ut/dm26_rp2/test_dm26_rp2_vr1_77.py`。

### 「離れた時、その下に〜があれば」＝ ZoneChangeEvent.evolution_sources
進化クリーチャーが場を離れると `CardMover._execute_move` が**先に
`clear_evolution_sources()` で進化元を解放**してから `ZoneChangeEvent` を publish する。
そのため誘発の解決時にはもう `card.evolution_sources` は空。離れる直前に解放した進化元
（その下にあったカード）は `ZoneChangeEvent.evolution_sources` に載せてあるので、
誘発条件は `card_count_matches` の `cards: {"ref": "event.evolution_sources"}` で判定する。
誘発は `active_zones: "any"` + `ignore_source_continuity: true` を付ける（離れた後に解決するため）。
`look_top_put_creature_to_battle`（上から N 枚を見て filter に合うクリーチャーを1体出し、
残りをシャッフルして山札の下へ）と組み合わせる。
参照: `dm26-rp2.VR.1/77`、テスト `tests/ut/dm26_rp2/test_dm26_rp2_vr1_77.py`。

### 初のフィールド（D2フィールド）と Dスイッチ
フィールドは `cards/field_card.py`（`FieldCard`）。手札から `use()` で「展開」してバトルゾーンへ
単体で出る（エレメント）。能力は他のカードと同じく `V2AbilityFactory` で生成され、バトルゾーン
入場時に `register_abilities` で購読される（`active_zones` 既定は battle なのでそのまま誘発する）。

`dm26-rp2.R.15/77`（Dの機動 ヴァイス・ヴァーチュー）の3能力:
- **G・ストライク**: 標準キーワード `g_strike` のみ（メタテキストは標準効果の明文化）。
- **自分のターンの終わりに引いてもよい**: `trigger {event: turn_end, player: controller}` +
  `draw {amount:1, max_amount:1, prompt}`。`max_amount` だけで `resolve_effect_amount` が
  0〜N を選ばせるため「引いてもよい」になる（`optional` は不要）。
- **Dスイッチ**: 下記の設定可能な共通メカニクス。

**Dスイッチは設定可能な共通メカニクス**。「[誘発]の時、D2フィールドをゲーム中で1度上下逆さまに
してもよい。そうしたら[後続効果]」で、**誘発も後続効果もカードごとに違う**。`d_switch` は
keyword グループに **object で** 置き、`trigger` と `effects` をカード側で指定する。
共通部分（ゲーム中で1度・任意の反転・「そうしたら」）だけ `build_d_switch_ability`
（`abilities/traits/d_switch_ability.py`）が組み立てる。

```json
"keyword": [
  "g_strike",
  { "ability_id": "d_switch",
    "label": "Dスイッチ：...",
    "flip_prompt": "...",
    "trigger": { "event": "attack_declared", "target": "controller" },
    "effects": [ ...後続効果... ] }
]
```

- **生成物**: `build_d_switch_ability` は `JsonTriggeredAbility` を返す。effects を
  `[ {flip_d2_field}, {packaged, connector:"then", effects:後続} ]` に組み、condition に
  「展開中1度」ガード `source_has_state(d_switch_flipped == false)` を AND する
  （カード側 `condition` があれば一緒に AND）。誘発と効果は標準の TriggerMatcher /
  EffectFactory に丸投げできるので、他の Dスイッチは JSON だけで追加できる。
- **展開中1度（再展開で再使用可）**: `FieldCard.d_switch_flipped`。`flip_d2_field` 効果
  （`effects/fields/flip_d2_field_effect.py`、発生源＝`source_card` を反転）が True にする。
  カード表記は「ゲーム中で1度」だが、D2フィールドは離れると反転状態がリセットされる
  （`reset_battle_state` で False に戻す）ため、再展開すれば再び使える。
- **任意の反転→「そうしたら」**: `FlipD2FieldEffect.resolve()` が反転可否を真偽で返し、後続
  packaged に `connector: "then"` を付けて**反転した時だけ**後続を実行する。断れば反転せず、
  後の誘発で再挑戦できる。
- **誘発が「自分（プレイヤー）への攻撃」**: trigger DSL に `target` matcher を新設
  （`abilities/v2/trigger_matcher.py`・`spec_schema.TRIGGER_KEYS`）。`target: "controller"/
  "opponent"` はプレイヤー、それ以外はカード参照として `event.target` と同一性比較する。
  「クリーチャーが自分を攻撃する時」＝`{event: attack_declared, target: "controller"}`。
- **無償実行（R.15 の後続）**: `execute_card_from_hand`（`type: non_creature`, `max_cost: 5`,
  `ignore_cost` 既定 True）。「その文明がすべて自分のマナゾーンにある」は legacy フィルタ
  （`card_predicates.matches_card_filter`）の新キー `civilizations_all_in_mana_zone: "self"`。
  `max_cost` を含むフィルタは DSL が弾かれ legacy 経路に落ちるためそこへ追加。validator にも
  許可キーを追加（`card_definition_validator._validate_card_filter`）。カードの全文明 ⊆
  マナゾーンの文明和。無色は空集合なので vacuous に True。
- 注意: keyword グループの中身は validator が検証しないため、`d_switch` の trigger/effects の
  打ち間違いはロード時に弾かれない（他のキーワード能力と同様）。カードごとに必ずテストする。

参照: `dm26-rp2.R.15/77`、テスト `tests/ut/dm26_rp2/test_dm26_rp2_r15_77.py`。

## ガードマン／スーパーガードマンと「攻撃できない能力の無視」（DM26-RP2 R.27/77）

- **ガードマン（`guardman`）はブロッカー系の「攻撃先変更」として実装**。置換効果に
  しない。`GameQuery.get_guardmen(attacker, target)` が候補（相手クリーチャーが自分の
  「他の」未タップクリーチャーを攻撃した時の自分のガードマン）を集め、
  `CombatManager.try_guardman()` が `try_block()` の直前で攻撃先を移し替える（使用時に
  自身をタップ）。プレイヤー攻撃には使えず、自分のクリーチャーが攻撃している時は自分の
  ガードマンも使えない。`abilities/keywords/guardman_ability.py` のマーカー能力＋registry
  登録。
- **スーパーガードマン（`super_guardman`）はバトル肩代わりの置換効果**で別実装
  （`SuperGuardmanAbility`、`BattleDeclaredEvent` に反応）。ただし ability_id が `guardman`
  を**部分文字列として含む**ため、`has_keyword_contains: "guardman"` のバフ対象には
  `guardman` と一緒に拾われる。
- **「『ガードマン』を持つクリーチャーすべてに付与」は `grant_rule` を3本**（speed_attacker /
  powered_breaker / ignore_own_attack_forbid）。filter は `has_keyword_contains: "guardman"`。
  `grant_rule` は **`rule` の中**に `scope` / `filter` / `ability` を書く（top-level に置くと
  registry の `_grant_ability` が `ability` を見つけられず落ちる）。
- **「攻撃できない能力を無視する」は `ignore_own_attack_forbid` マーカー**
  （`abilities/traits/ignore_own_attack_forbid_ability.py`）。`AttackValidator` が
  `forbids_attack` / `forbids_attack_player` を走査する際、攻撃クリーチャーがこの能力を持つなら
  **発生源が攻撃クリーチャー自身（`card is attacker`）の禁止だけをスキップ**する。他カード由来の
  禁止や `temporary_combat_restrictions`（外部由来）は無視しない。召喚酔いは付与した
  `speed_attacker` で解消する。

参照: `dm26-rp2.R.27/77`、テスト `tests/ut/dm26_rp2/test_dm26_rp2_r27_77.py`、
`tests/ut/common/test_guardman_ability.py`。

## legacy `effect_id` と v2 `type` の使い分け（表記方針）

同じ効果概念が両系統に存在する（`move_card`(legacy) / `move`(v2)、`draw`、`destroy`、
`modify_power`、`battle`、`tap`、`temporary_combat_restriction` 等）。実装時期の違いから
既存カード JSON では両方が混在しているが、以後は次の方針で書く:

- **新規実装は v2 `type` を優先**する。v2（`effects/effect_factory.py` の
  `EffectFactory.BUILDERS`）に同等機能が無い場合のみ legacy `effect_id`
  （`effects/registry.py` の `EFFECT_BUILDERS`）を使う。
- **既存の legacy 効果は無理に変換しない**。両系統は別パイプラインで挙動・受け付ける
  オプションが微妙に異なるため、動作確認済みの effect を機械的に置換すると回帰を生む。
  変換する場合はそのカードのテストを必ず回す。
- 可読性のため、**同一カード内・同一能力内ではどちらか一方に揃える**ことを目指す。
- `type` と `effect_id` の取り違えは `Unknown v2 effect type` / `Unknown effect id` で
  落ちる（特に分岐は必ず `"type": "if"`）。

参照: `docs/JSON_SPEC.md`（効果の2系統）、`effects/effect_factory.py`、`effects/registry.py`。
