# カード定義 JSON 仕様（構造化 v2）

カード能力は構造化 v2 形式のみをサポートする。legacy のリスト形式 `abilities: [{...}]`（非空）はロード時に拒否される。実装の正は次のとおり:

- 能力グループの検証: `card_db/v2_ability_parser.py`
- スキーマキー: `abilities/v2/spec_schema.py`
- イベント一覧: `abilities/v2/event_map.py`
- condition 一覧: `core/condition_registry.py`
- v2 効果 type: `effects/effect_factory.py`（`EffectFactory.BUILDERS`）
- legacy 効果 id: `effects/registry.py`（`EFFECT_BUILDERS`）
- キーワード等の能力 id: `abilities/registry.py`（`ABILITY_BUILDERS`）

## ファイル形式

```json
{
  "cards": {
    "<card_id>": { ...カード定義... }
  }
}
```

メタデータファイル（`data/impl_card_metadata/`）も同じ `cards` ラッパー形式で、`<card_id>` キーに `name_ja` / `effect_name_ja` / `race_ja` / `effect_texts_ja`（ツインパクトは `creature` / `spell` 面ごとにも）を書く。`name_ja` は可読性のため `impl_cards` 側にも置く。

デッキ（`data/decks/`）:

```json
{
  "name": "Sample Deck",
  "cards": [
    { "id": "<card_id>", "count": 4 }
  ]
}
```

デッキ検証は合計 40 枚を要求する。

## カード共通キー

| キー | 必須 | 説明 |
|---|---|---|
| `kind` | はい | `creature` / `spell` / `twinpact` / `castle` / `cross_gear` / その他のカードタイプ名（タマシード等は GenericCard のひな形） |
| `name_ja` | はい | 表示用の日本語名。実カードも `impl_cards` 側に置く |
| `effect_name_ja` / `race_ja` / `effect_texts_ja` | 条件付き | 日本語メタデータ（実カードは metadata ファイルに分離。ロード後はクリーチャーの `race_ja` が必須） |
| `cost` | はい | コスト |
| `civilizations` | はい | `fire` / `water` / `nature` / `light` / `darkness` の配列（単色でも配列） |
| `power` | creature | 通常パワー |
| `hyper_power` | 任意 | ハイパーモード中の基準パワー |
| `special_types` | 任意 | `evolution` / `dream` / `hyper mode` / `neo` / `galaxy`（城のみ）。日本語表記も正規化される |
| `abilities` | はい | v2 能力グループ（下記）。なしは `{}` または `[]` |
| `effects` | spell | 呪文解決時の効果配列 |
| `creature` / `spell` | twinpact | 各面のカード定義（`id` 不要） |

## 能力グループ

```json
"abilities": {
  "keyword": [],
  "static": [],
  "triggered": [],
  "activated": [],
  "replacement": []
}
```

**すべての構造化能力 spec（keyword の object 形式含む）には `ability_id`（能力インスタンスの識別名）を付ける**（`tests/card_db_tests/test_dm26_rp1_v2_authoring.py` が要求）。v2 内で legacy 効果を呼ぶ場合は `effect_id`、v2 効果は `type` を使う。

### keyword

文字列 ID、またはオプション付き object。

```json
"keyword": [
  "blocker",
  "double_breaker",
  {
    "ability_id": "triple_breaker",
    "active_if": { "type": "source_has_state", "state": "hyper_mode" }
  },
  { "ability_id": "ninja_strike", "mana_count": 5 },
  { "ability_id": "evolution", "civilizations": ["water"] }
]
```

主な登録済み ID（正確な一覧は `abilities/registry.py` の `ABILITY_BUILDERS`）:

- ブレイカー: `w_breaker` / `double_breaker`, `t_breaker` / `triple_breaker`, `q_breaker` / `quad_breaker` / `quadruple_breaker` / `quatro_breaker`, `world_breaker`, `powered_breaker`, `shield_breaker`
- 戦闘・移動: `blocker`, `speed_attacker`, `mach_fighter`, `slayer`, `unblockable`, `untouchable`, `unblockable and untouchable`（束ID）, `just_diver`, `escape`, `separation_lock`, `power_attacker`（`amount` 必須。攻撃中だけ +N の常在型）, `powered_blocker`（`amount` 必須。ブロック中だけ +N＝パワード・ブロッカー）, `battle_power`（`amount` 必須。バトル中だけ +N。攻撃・ブロック・強制バトルすべて対象）, `must_attack`（このクリーチャーは可能なら攻撃する。一時付与で「次の自分のターンまで攻撃させる」等に使う）
- シールド: `shield_trigger`, `conditional_shield_trigger`, `g_strike`, `shield_force`, `shield_saver`, `shield_go`（破壊→表向きシールド化＋表向きで離れる時かわりに墓地）
- 召喚・コスト: `g_zero`, `sympathy`, `soulshift`（進化元のコスト分だけ自身の召喚コストを軽減。下限は `min_cost` 既定1。進化元の選択は「召喚宣言→進化元選択→マナ支払い」の順で先に確定し、確定前のコスト計算では最大軽減を仮定する）, `alternative_summon_cost`, `graveyard_summon`, `play_from_zone`, `summon_top_deck_creature`
- 進化: `evolution`, `hand_evolution`, `mana_evolution`（`civilizations` で進化元の文明条件）
- 攻撃宣言時の手札宣言: `revolution_change`（`attack_creature` に攻撃中クリーチャーの filter DSL を書く）
- シノビ: `ninja_strike`, `ura_ninja_strike`
- 常在・制約: `cannot_cast_spells`, `opponent_attack_mandatory`, `attack_player_lock`, `tap_to_play`, `element_entry_lock`, `creature_entry_lock`, `enter_turn_attack_lock`, `grant_ability`, `z_rush`, `mana_number`, `power_per_card_in_zone`, `look_top_of_deck`
- クロスギア: `cross_grant`, `cross_on_ally_enter`, `cross_on_crossed_attack_recross`, `cross_leave_saver`

### triggered

```json
{
  "ability_id": "<card>_enter_trigger",
  "trigger": { "type": "enter_battle", "card": { "ref": "source" } },
  "condition": { "type": "turn_player_is", "player": "controller" },
  "active_if": { "type": "card_state", "card": "source", "state": "shield_face_up", "value": true },
  "active_zones": ["shield"],
  "requires_trigger_declaration": false,
  "trigger_declaration_optional": true,
  "targets": [
    {
      "id": "chosen_card", "chooser": "controller",
      "from": { "player": "controller", "zone": "hand" },
      "filter": { "card_type": "creature" },
      "min": 0, "max": 1, "optional": true
    }
  ],
  "effects": [ { "effect_id": "draw", "amount": 1 } ],
  "label": "デバッグ表示用",
  "ignore_source_continuity": false
}
```

| キー | 説明 |
|---|---|
| `trigger` | 必須。誘発イベントの照合 DSL（下記） |
| `condition` | 任意。**トリガー発火時**に `ConditionEvaluator` で評価。解決時に評価したい条件は効果側の `type: "if"` に書く |
| `active_if` | 任意。発生源の状態ゲート（ハイパーモード中、表向き等）。`condition` と AND |
| `active_zones` | 誘発できる領域。**未指定はバトルゾーンのみ**。`["shield"]` や `"any"` |
| `requires_trigger_declaration` | `true` で、この誘発を解決キュー選択前の「宣言タイミング」で宣言対象にする。手札など非公開領域から使う誘発に指定する |
| `trigger_declaration_optional` | 宣言が任意かどうか。既定 `true`。`false` なら宣言タイミングで自動的に宣言済みにする |
| `targets` | 効果解決前の対象選択。結果は `{"ref": "<id>"}` で参照 |
| `effects` | 解決する効果列 |
| `ignore_source_continuity` | `true` で発生源が領域を離れた後も解決する（破壊誘発の自己再帰など）。`source_info` を参照する effect は LKI で情報参照できるため、既存 continuity チェックで不当に解決不能にならないよう短期互換として同等に扱う |

`requires_trigger_declaration` は宣言順だけを固定する。宣言済みになった後の解決順は通常の同一プレイヤー効果と同じく、プレイヤーが選ぶ。

### 革命チェンジ

`revolution_change` は keyword 能力として書く。攻撃中クリーチャーの条件は `attack_creature` に既存の filter DSL で指定する。文明を配列で書いた場合は「いずれかの文明」として扱う。

```json
{
  "ability_id": "revolution_change",
  "attack_creature": {
    "civilization": ["light", "nature"],
    "power": { "gte": 4000 }
  }
}
```

攻撃宣言時に手札から宣言候補になり、解決時にも現在の攻撃クリーチャーで条件を再確認する。入れ替えは `CardMover.swap` による事前検証付きの移動として処理され、どちらかの移動が置換される場合は置換を実行せず革命チェンジ全体が失敗する。

#### trigger DSL

リーフトリガーで使えるキー: `type`（または `event`）, `subject`, `attacker`, `player`, `card`, `filter`, `from_zone`, `to_zone`, `reason`。`card` / `attacker` は `{"ref": "source"}` 等の ref。`reason` は文字列または `{"in": [...]}` 等の比較 object。未知キーはバリデーションで落ちる。

イベント名（`abilities/v2/event_map.py`）:

`attack_declared`, `attack_ended`, `battle_declared`, `battle_start`, `battle_won`, `battle_lost`, `battle_end`, `block_declared`, `card_chosen`, `destroy`, `destroy_attempt`, `enter_battle`, `shield_break`, `shield_break_attempt`, `spell_cast`, `summon`, `tap`, `untap`, `turn_start`, `turn_end`, `zone_change`, `zone_change_attempt`

バトル系イベントの順序（`core/combat_manager.py`）: `battle_declared`（バトル中の常在・置換の開始）→ `battle_start`（「バトルする時」誘発、ここで解決）→ 両者が残っていればバトル実行 → `battle_won` / `battle_lost`（同パワーは両者 `battle_lost`）→ 敗者破壊と誘発解決 → スレイヤー破壊 → `battle_end`（「バトルの後」。バトル不成立時は発生しない）。`battle_declared` / `battle_start` / `battle_end` は `card` = 攻撃側、`target` = 防御側を持つ。

（別名: `cast` / `cast_spell` → `spell_cast`、`zone_changed` → `zone_change` 等。`draw` イベントは**存在しない** — ドロー誘発は `zone_change` + `reason` で書く。[imp_tips.md](imp_tips.md) 参照。）

複合トリガー（or / and / not）:

```json
"trigger": {
  "type": "or",
  "triggers": [
    { "type": "zone_change", "card": { "ref": "source" }, "to_zone": "shield" },
    { "type": "turn_start", "player": "self" }
  ]
}
```

`not` は `trigger`（または `condition`）に単一で書く。入れ子可。能力は全サブトリガーのイベント型を購読し、各リーフは自分のイベント型以外を自動で弾く。

ゾーン名は正規名（`battle`, `deck`, `graveyard`, `hand`, `mana`, `shield`）で書く。`mana_zone` のような別名は trigger 照合でマッチしない。

### activated（起動型）

```json
{
  "ability_id": "<card>_activate",
  "timing": { "active_zone": "battle", "step": "main" },
  "condition": { "type": "always" },
  "effects": [ ... ]
}
```

`timing` のキーは `active_zone` / `active_zones` / `step` のみ。解決時は `PackagedEffect` がキューに積まれる。

### replacement（置換）

```json
{
  "ability_id": "shield_break_bottom_deck_replacement",
  "type": "shield_break",
  "attempt": { "event": "shield_break_attempt", "breaker": { "ref": "source" } },
  "active_if": { "type": "source_has_state", "state": "hyper_mode" },
  "replace_with": {
    "cancel_event": true,
    "actions": [
      {
        "type": "move_event_card",
        "card": { "ref": "event.shield_card" },
        "from_zone": "shield", "to_zone": "deck",
        "reason": "shield_break_replacement",
        "apply_replacements": false
      }
    ]
  },
  "after_replacement_batch": {
    "effects": [
      { "type": "draw", "player": "each_player", "amount": { "ref": "replacement_count" } }
    ]
  }
}
```

- `attempt` で使えるキー: `event` / `type`, `breaker`, `card`, `card_filter`, `from_zone`, `to_zone`。対象イベントは `shield_break_attempt` / `zone_change_attempt` / `destroy_attempt`。
- `active_zones`: 誘発と同じく、置換が働く領域。**未指定はバトルゾーンのみ**。マナ／墓地に置かれたクリーチャーの置換が他カードのイベントに誤反応するのを防ぐ。手札からの身代わりは `["hand"]`、表向きシールドで働く G城・シールド・ゴーは `["shield"]`、領域を問わないものは `"any"` を明示する。
- `replace_with` で `cancel_event` と置換アクションを指定。`costs` で置換コスト（「かわりに〜してもよい」）も書ける。
- `after_replacement_batch` は一連の置換が終わった後に解決する効果列。`{"ref": "replacement_count"}` で置換回数を参照できる。
- `type: "shield_break_redirect"` + `rule.kind: "break_this_shield_instead"` は registry の `break_this_shield_instead` へ橋渡しされる。「かわりにこのシールドをブレイクする」置換で、このシールド自身が直接ブレイク対象の時も任意で適用できる。置換後の `ShieldBreakAttemptEvent` に `consume_remaining_breaks` を立てるため、複数ブレイク全体をこのシールド1つへ差し替える。

### static（常在型ルール修飾）

`type` で機構を指定する。許容される type（`card_db/v2_ability_parser.py` の `STATIC_TYPES`）:

`attack_rule`, `block_rule`, `break_modifier`, `cast_rule`, `choice_replacement`, `cost_modifier`, `cost_payment_rule`, `cross_rule`, `enter_battle_rule`, `grant_rule`, `mana_rule`, `power_modifier`, `summon_rule`, `target_rule`

**注意: type がパーサを通っても、エンジンに配線されていなければ `StaticAbility` プレースホルダとして保持されるだけで何もしない。** 使う前に `card_db/v2_ability_factory.py` で配線状況を確認し、未配線ならテストを追加してから engine hook を実装する。配線済みの例:

- `cost_modifier`（`applies_to` が他カード）→ `SummonCostReductionAbility`。自分のクリーチャーの召喚コスト軽減。`modifier: { amount, min_cost, per_turn, optional }`。詳細は [imp_tips.md](imp_tips.md)。
- `cost_modifier`（`applies_to.card: "self"`）→ `SelfSummonCostModifierAbility`。自身の召喚コストを増減（例: 「手札から召喚するなら+3」）。`applies_to.from_zone` で適用元ゾーンを限定し、`modifier: { amount, min_cost }` を指定する。
- `attack_rule`（`rule.kind: "must_attack_this"`）→ `AttackLureAbility`。「相手のクリーチャーが攻撃するなら、可能ならこのクリーチャーを攻撃する」。攻撃を強制せず、攻撃先候補をこのクリーチャー（正規の攻撃対象になれる場合のみ）へ絞る。`condition: { type: "source_has_state", state: "hyper_mode" }` で活性条件を付けられる。
- `attack_rule`（`rule.kind: "cannot_attack_player"`）→ `AttackPlayerLockAbility`。`scope`（既定 `self`）と任意の `filter` で対象を絞り、プレイヤーへの攻撃だけを禁止する。`condition: { "type": "not", ... }` は `active_if` として registry 能力へ渡せる。
- `summon_rule`（`rule.kind: "from_mana"` 等）→ `PlayFromZoneAbility`。別ゾーンからの召喚許可 + `follow_up` 効果。詳細は [imp_tips.md](imp_tips.md)。

「マナ武装」は static の専用 type ではなく、**condition 能力語 `mana_armor`**（後述の condition 一覧）を各能力・効果の `active_if` に書いて表現する。

## 効果（effects）

効果は 2 系統あり、キーで振り分けられる:

- **v2 効果**: `"type": "..."` で指定。`EffectFactory` が組み立てる。
- **legacy 効果**: `"effect_id": "..."` で指定。`effects/registry.py` が組み立てる。

`type` と `effect_id` を取り違えると `Unknown effect id` / `Unknown v2 effect type` で落ちる（特に `if` は必ず `"type": "if"`）。

同じ効果概念が両系統に存在する場合（`move`/`move_card`、`draw`、`destroy` 等）の使い分け方針は [imp_tips.md](imp_tips.md) の「legacy `effect_id` と v2 `type` の使い分け」を参照（新規は v2 `type` 優先・既存 legacy は無理に変換しない）。

### v2 効果 type

`draw`, `discard`, `move`, `destroy`, `tap`, `untap`, `select`, `choose_number`, `execute`, `modify_power`, `battle`, `if`, `choice`, `alternative_effect`

よく使う形:

```json
{ "type": "select", "candidates": "opponent_creatures", "filter": {...}, "store_as": "chosen", "optional": true, "prompt": "..." }
{ "type": "if", "condition": {...}, "then": [...], "else": [...] }
{ "type": "battle", "attacker": { "ref": "event.card" }, "defender": { "ref": "chosen" }, "connector": "then" }
{ "type": "move", "from_zone": "deck", "to_zone": "mana", "selection": "top", "amount": 1, "tapped": true }
{ "type": "move", "cards": { "ref": "chosen" }, "from_zone": "battle", "to_zone": "deck", "destination_position": "top" }
{ "type": "execute", "target": { "ref": "card_to_execute" }, "without_cost": true }
{ "type": "choice", "selector": "opponent", "prompt": "...", "choices": [ { "label": "...", "effects": [...] }, ... ] }
```

`select` の `candidates`: `creatures` / `all_creatures`, `opponent_creatures`, `own_creatures`, `own_other_creatures`, `opponent_battle_zone`, `own_battle_zone`、またはゾーン名（`player` 併用）。

`choice` は `selector`（または `choosing_player`）で分岐を選ぶプレイヤーを指定できる（例: `"opponent"` で「相手は破壊するか山札の上に置くかを選ぶ」）。分岐内の効果はコントローラー基準で解決される。`move`（ref 移動）は `destination_position: "top"` で移動先ゾーンの一番上に置ける（既定は一番下）。

### legacy 効果 id（主要なもの）

`effects/registry.py` の `EFFECT_BUILDERS` が正。

- ドロー・手札: `draw`, `discard`（`target_player: "opponent"` で相手が選んで捨てる）, `discard_hand_then_draw`, `look_top_choose_to_hand`
- 山札上を見て出す: `look_top_same_cost_creatures_to_battle`（上から N 枚が全て同コストのクリーチャーなら全て出す）, `look_top_put_creature_to_battle`（上から `amount` 枚を見て `filter` に合うクリーチャーを1体出す＝`optional` で任意。残りはシャッフルして山札の下へ）
- 領域移動: `move_card`, `put_creature_from_zone`, `put_creature_from_multi_zone`, `execute_card_from_zone`, `execute_card_from_hand`, `mill`, `return_from_graveyard`, `bounce_own_creature`, `bounce_opponent_creature`, `bounce_own_battle_card`, `bounce_opponent_battle_card`, `charger`（呪文解決後の最終移動をマナへ切り替えるマーカー）
- シールド: `add_deck_to_shield`, `add_hand_to_shield`, `add_shield_to_hand`, `shield_plus`（山札上から裏向きで既存シールド束へ追加）, `break_shield`, `creature_break_shield`（breaker を ref で指定）
- 破壊・戦闘: `destroy_creature`, `destroy_multiple`, `battle_two_creatures`, `tap`, `untap`, `freeze_untap`（ターン開始アンタップのみ阻止）, `lock_untap`（アンタップ全般を阻止）, `opponent_taps_own_creature`
- 修飾: `power_modifier_self`, `power_modifier_opponent_creature`, `multiply_power`（このターン中パワーを `factor` 倍。`target` 省略時は発生源。`target: {"ref": ...}` で先に選んだクリーチャーを対象にできる）, `wins_all_battles`, `temporary_combat_restriction`（`restrictions`: `attack` / `block` / `attack_player`＝プレイヤー攻撃のみ禁止）, `temporary_ability`（`ability` は dict で渡す）
- ターン進行: `grant_extra_turn`（`target_player`＝既定 `self`。指定プレイヤーに追加ターンを1回与える。「このターンの後に〜のターンを追加する」。現在ターン終了後に挿入され、正規の手番ローテーションは消費しない＝相手ターン中に得れば「相手→自分(追加)→自分(通常)」と連続手番になる。`GameState.pending_extra_turns` ＋ `advance_to_next_turn` で処理）
- 複合・制御: `packaged`, `select_then`（`effect` 単発のほか `effects` リストで同じ対象へ順番に適用できる。対象効果: `bounce` / `destroy` / `tap` / `untap` / `temporary_combat_restriction` / `modify_power`（`duration` 付きで期間限定）/ `battle` / `move_card`）, `look`, `reveal`, `reveal_cards`, `count`, `for_each`, `select_n`, `select_within_total_power`, `if_stored_card_matches`, `reveal_stored_card`, `count_matching`, `gather_matching`, `for_each_stored`, `repeat`, `choose_n_effects`, `once_per_turn_gate`, `once_per_turn_mark`
  - `select_within_total_power` の `max_total_power` は数値のほか `"source_power"`（legacy）、`{"ref":"source_info.power"}` で**発生源の現在パワーまたは LKI**を上限にできる（マナ武装等の修整込み）。

`look` / `reveal` / `reveal_cards` / `count` / `for_each` は stored / selected / zone 由来のカード集合を再利用する汎用 effect。主なキーは `source`（`stored` / `selected` / `zone`）, `store_key`, `zone`, `player`, `amount`, `from`, `condition`, `count_key`, `effect`。

`look` は「見る」効果で、見たカードは相手に公開しない。見たカードを後続で参照する場合は `store_as` / `store_key` に保存する。

`reveal_cards` は「カードをN枚表向きにして、表向きにしたカードを `store_as` へ保存する」ための公開効果。カードは移動しない。`amount: 1` では既定でカード単体を保存し、複数枚ではリストを保存する（1枚でもリストにしたい場合は `as_list: true`）。表向きにする処理は全員に公開されるため、`to` / `reveal_to` のような公開先指定は使わない。

```json
{ "effect_id": "reveal_cards", "from_zone": "deck", "amount": 1,
  "from": "top", "store_as": "revealed_card" }
```

`reveal_cards` は `optional: true`（＋任意の `prompt`）で「表向きにしてもよい」を表現できる。断ると何も公開せず、`store_as` には `null`（`as_list` 時は空リスト）を入れて False を返すため、後続の `card_matches {ref: ...}` 系条件は不成立になり山札の一番上が温存される。

共通オプション:

| キー | 説明 |
|---|---|
| `connector` | `after`（その後、既定）/ `then`（そうしたら＝直前の効果を「試みた」場合のみ実行） |
| `optional` / `prompt` | 任意効果とその表示文 |
| `amount` / `max_amount` / `min_amount` | 固定枚数 / 「〜まで」（0..N の枚数選択）。`{"ref": ...}` も可 |
| `store_as` | 結果カードを package context へ保存。後続から `{"ref": "<name>"}` で参照 |
| `from_zone` / `to_zone` / `selection` | 移動系。`selection`: `choose` / `top` / `bottom` / `first_matching` / `source_card` |
| `face_options` / `shield_placement` | シールド配置時の向き / 重ね先スロット選択 |
| `target_player` | 効果の対象プレイヤー（効果ごとに意味が異なる。[imp_tips.md](imp_tips.md) の discard 項参照） |
| `duration` | `{"type": "until_end_of_turn"}` 等の object 形式。`permanent` で永続（期間終了しない。クリーチャーへの恒常的な能力付与に使う） |

共通キーの alias 正規化（`effects/registry.py` の `COMMON_KEY_ALIASES`）:

`build_effects` の入口で、同じ概念を表す alias を canonical キーへ正規化する。これにより **どの effect_id でも同じキー**で書ける（例: `count` は常に `amount` として、`player` は常に `target_player` として扱われる）。canonical が既にあれば上書きしないため既存 JSON と互換。

| alias | canonical |
|---|---|
| `effect_id` | `id` |
| `count` | `amount` |
| `up_to` | `max_amount` |
| `player` | `target_player` |
| `source_zone` | `from_zone` |
| `destination_zone` | `to_zone` |
| `shield_destination` | `shield_placement` |
| `stack_on` | `shield_stack_on` |
| `tap` | `tapped` |
| `chooser` | `selector` |
| `package_connector` | `connector` |
| `position` | `from` |

## condition DSL

`condition` / `active_if` は **object 形式のみ**（文字列はバリデーションで落ちる）。type 一覧（`core/condition_registry.py` が正）:

`always`, `and`, `or`, `not`, `source_has_state`, `source_zone_is`, `event_actor_is`, `event_card_matches`, `event_card_is`, `event_zone_change_matches`, `event_player_is`, `card_count_matches`, `mana_armor`, `first_time_each_turn`, `once_per_turn`, `once_per_turn_available`, `battle_result_matches`, `choice_history_matches`, `player_zone_count`, `turn_player_is`, `turn_player`, `card_state`, `card_matches`

`event_card_is`（`card` 既定 `source`）: イベントのカードが指定参照と同一かを判定。「自分の**他の**クリーチャーが出た時」のような自己除外は `{"type":"not","condition":{"type":"event_card_is","card":"source"}}`。

例:

```json
{ "type": "source_has_state", "state": "hyper_mode" }
{ "type": "card_state", "card": "source", "state": "shield_face_up", "value": true }
{ "type": "card_count_matches",
  "from": { "player": "controller", "zone": "battle" },
  "filter": { "card_type": "creature" },
  "op": "gt", "value": { "ref": "opponent.creature_count" } }
{ "type": "mana_armor", "civilization": "light", "count": 3 }
{ "type": "turn_stat", "stat": "cards_drawn", "player": "controller", "op": "gte", "value": 2 }
```

`turn_stat`（このターンの行動集計＝`TurnStatsManager`）: `stat`（`cards_drawn` / `spells_cast` / `non_creature_executed`）を `player`（既定 controller）について `op`/`value` と比較。「このターンに〜していなければ攻撃できない」は static `attack_rule` の `rule.kind: "cannot_attack_unless"` + `rule.condition` と組み合わせる。

`mana_armor`（マナ武装の条件能力語）: 「自分のマナゾーンに `civilization`（複数は `civilizations`）が `count` 枚以上（既定3）あれば真」。`card_count_matches`（マナ＋文明）へ展開される。パワー増加以外のマナ武装効果は、これを各能力・効果の `active_if` / `condition` に書く。

condition type の追加手順: `core/condition_registry.py` の `CONDITION_DEFINITIONS` に登録 → `core/condition_evaluator.py` に評価メソッド → 必要なら Validator を登録 → `tests/ut/test_condition_filter_dsl.py` にテスト。

## filter DSL

カードの絞り込み（`CardFilterEvaluator`）。主なキー: `card_type`（`creature` / `spell` / `element` / `non_creature` / `castle` 等）, `special_type`（`galaxy` 等＝特殊タイプの絞り込み）, `civilizations`, `race_ja`, `cost`, `power`, `shield_face_up`, `tapped`, `is_evolution`, `controller`, `has_keyword`, `has_keyword_contains`。

城と G城はどちらも `card_type: "castle"`。**G城のみ**を判定するには `special_type: "galaxy"` を併用する（`{"card_type": "castle", "special_type": "galaxy"}`）。`not` と組み合わせれば「G城でない城」も書ける。

`race_ja` は日本語種族名を見る。期待値文字列が実際の日本語種族名に含まれれば一致する（例: `"ドラゴン"` は `"アーマード・ドラゴン"` に一致）。英語種族用の `race` / `races` フィルタは使わない。

`has_keyword` は能力 ID の完全一致、`has_keyword_contains` は **部分一致**（指定文字列を ability_id に含むか）。`has_keyword_contains: "guardman"` は `guardman` だけでなく `super_guardman` も拾う。「『ガードマン』を持つクリーチャー」のようにキーワードの族をまとめて対象にするときに使う。

数値キーは比較 object を取る: `eq` / `ne` / `lt` / `lte` / `gt` / `gte` / `contains` / `not_contains` / `in` / `not_in`（`core/dsl_compare.py`）。論理は `and` / `or` / `not`。

```json
"filter": {
  "card_type": "creature",
  "cost": { "lte": { "ref": "controller.zone_count.mana" } },
  "is_evolution": false
}
```

自己コスト修飾は `modifier.per_count` で枚数比例にできる。

```json
{
  "type": "cost_modifier",
  "applies_to": { "card": "self", "from_zone": "hand" },
  "modifier": {
    "amount": -3,
    "min_cost": 1,
    "per_count": {
      "from": { "player": "controller", "zone": "battle" },
      "filter": { "card_type": "element", "cost": { "lte": 3 } }
    }
  }
}
```

`temporary_ability` は `scope`（例: `own_creatures`）を指定すると、解決時点の対象すべてへ一時能力を付与する。

## ref DSL

`{"ref": "..."}` の明示参照のみ解決する（`core/ref_resolver.py`）。文字列を暗黙参照として評価しない。主な参照先:

| ref | 内容 |
|---|---|
| `source` | 能力の発生源カード（城の能力なら城自身。**出たクリーチャーではない**） |
| `source_info.<property>` | 発生源の情報参照。発生源が有効なら現在値、離れていれば離れる直前の LKI を返す。例: `source_info.power`, `source_info.cost`, `source_info.contained_card_count` |
| `event.card` / `event.attacker` / `event.shield_card` / `event.moved_card` | 誘発イベントの対象 |
| `event.evolution_sources` | 場を離れる移動の `ZoneChangeEvent` が持つ、離れる直前に解放された進化元（その下にあったカード）のリスト。「離れた時、その下に〜があれば」を `card_count_matches` の `cards` で判定する |
| `controller.zone_count.<zone>` / `opponent.zone_count.<zone>` | ゾーン枚数（`<zone>` はゾーン名。シールドはスロット数） |
| `controller.creature_count` / `opponent.creature_count` | バトルゾーンのクリーチャー数 |
| `source.cost` / `source.power` 等 | legacy scalar 参照。新規 JSON では `source_info.cost` / `source_info.power` を推奨。`source` 単体は live card 参照として残る |
| `<store_as名>` / `<targets の id>` | 保存済みの選択結果 |
| `replacement_count` | 置換回数（replacement の after batch 内） |

ref は filter 解決時（候補列挙時）に遅延評価される。誤った ref パスはロード時には通り、**解決時に初めて例外になる**ため、テストで実際に候補が列挙できることを確認する。

`source_info` は `{"from":"source_info","property":"contained_card_count"}` の形でも使える。発生源自身の情報を見る効果だけに使い、盤面・手札・墓地など現在のゲーム状態を見る効果は通常の query / target / filter で解決時の状態を参照する。

## バリデーションで落ちる例

- 非空のリスト形式 `abilities`（legacy）
- `condition` / `active_if` が文字列
- 未知の trigger / attempt / timing / target キー、未知のイベント名・condition type
- `filter` の未知キー、比較 object の未知演算子
- `{"ref": 1}` のような非文字列 ref、保存値名の文字列直書き
- eval 前提の条件（`{"type": "eval", ...}`）

## JSON 構造ツリー（要約）

```text
cards.<card_id>
├─ kind / name_ja
├─ cost / civilizations[] / power / hyper_power / race_ja / special_types[]
├─ effects[]                  # spell: 解決時効果（effect_id / type）
├─ creature / spell           # twinpact: 各面の定義
└─ abilities
   ├─ keyword[]               # "id" 文字列 or { ability_id, active_if, ...オプション }
   ├─ static[]                # { type, ability_id, condition?, ... }
   ├─ triggered[]             # { ability_id, trigger, condition?, active_if?,
   │                          #   active_zones?, requires_trigger_declaration?,
   │                          #   targets?, effects[] }
   ├─ activated[]             # { ability_id, timing, effects[] }
   └─ replacement[]           # { ability_id, type, attempt, active_if?,
                              #   active_zones?, replace_with,
                              #   after_replacement_batch?, costs? }
```
