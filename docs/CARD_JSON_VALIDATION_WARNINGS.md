# カード JSON validator warning 機能

このドキュメントは、`tools/card_db_cli.py validate` が出す warning の仕様をまとめたものです。warning は「カード JSON の構造的な不整合（実装上は無視されるキー・表記ゆれ・接続キー漏れ）」をレビュー対象として拾うためのものです。

warning はヒューリスティックではなく **構造的な事実**（特定キーの有無・別名・未知の値）を検出します。文章（カードテキスト）の解析による推測は行いません。

## 実行方法

```powershell
python tools/card_db_cli.py --card-dir data/impl_cards validate
```

warning は `WARNING:`、error は `ERROR:` として出力します。warning があっても error がなければ終了コードは成功のままです。

現時点の `data/impl_cards` は warning ゼロです。

```text
OK: 90 cards
```

warning が出る場合の例:

```text
WARNING: W_ZONE_ALIAS: card_id=...; card_name=...; path=...rule.zones[0]; message=zone alias 'mana_zone' is accepted but inconsistent; possible_fix=use canonical zone name 'mana'
OK: 90 cards (1 warnings)
```

各 warning は次を含みます。

| 項目 | 内容 |
|---|---|
| `card_id` | カード ID。ツインパクト面の warning も親カード ID で出す。 |
| `card_name` | `name_ja` / `id` の順で決める表示名。 |
| `code` | warning code。後述。 |
| `path` | JSON path 風の位置。修正対象の近辺を指す。 |
| `message` | 検出理由。 |
| `possible_fix` | 典型的な修正案。 |

## 実装位置

| ファイル | 役割 |
|---|---|
| `card_db/card_definition_validator.py` | warning の実体。`ValidationWarning`, `validate_card_warnings`, 各 `W_*` / `E_UNKNOWN_CARD_TYPE` 判定。 |
| `card_db/database.py` | `CardDatabase.validate_warnings()`。DB 全体とツインパクト面を走査する。 |
| `tools/card_db_cli.py` | `validate` 実行時に warning を表示する。error があれば従来通り失敗。 |
| `tests/card_db_tests/test_validation_warnings.py` | warning/error 分離、各 warning code、回帰ガードの単体テスト。 |

## Warning / Error 一覧

### `W_ZONE_ALIAS`

zone 系キーに別名が使われている場合に出ます。ランタイムは別名も受け付けますが、表記をそろえるために canonical 名へ寄せます。

| alias | 推奨表記 |
|---|---|
| `battle_zone` | `battle` |
| `grave` | `graveyard` |
| `hand_zone` | `hand` |
| `mana_zone` | `mana` |
| `shield_zone` | `shield` |
| `shields` | `shield` |

対象キー: `active_zone`, `active_zones`, `from`, `from_zone`, `source_zone`, `to`, `to_zone`, `destination_zone`, `zone`, `zones`, `allow_from_zone`, `allow_from_zones`, `block_from_zones`。

値が比較式 (`{"ne": "shield"}` など) の場合も中の scalar を再帰的に見ます。

### `W_IGNORED_OPTIONAL`

effect 実装が読まない optional 系キーが書かれている場合に出ます。死にキー（書いても挙動が変わらない）を拾います。

検出ルール:

- `may` / `is_optional` は標準 effect flag ではないため常に warning。
- `optional` は、既知の optional-aware effect 以外に書かれている場合 warning。

例: `draw` は `optional` を読まず、任意ドローは `amount` + `max_amount`（+ `prompt`）で表現します。そのため `draw` に `optional` を付けると死にキーとして warning になります。

既知の optional-aware effect / v2 `type` の一覧は `card_definition_validator.py` の `OPTIONAL_AWARE_EFFECT_IDS` / `OPTIONAL_AWARE_V2_TYPES` を参照してください。新しい effect が `optional` を読むようになったら、この allow list を更新します。

### `W_MISSING_DEPENDENCY_KEY`

stored value を使う複合 effect に、実装上ほぼ必須のキーが足りない場合に出ます。

| effect | 必須候補 |
|---|---|
| `count_matching` | `source`, `store_as` |
| `count` | `source`, `count_key` |
| `for_each` | `source` |
| `for_each_stored` | `source` |
| `gather_matching` | `store_as` |
| `if_stored_card_matches` | `key` |
| `repeat` | `count_key` |
| `select_n` | `count_key`, `store_as` |
| `select_within_total_power` | `max_total_power`, `store_as` |

新しい複合 effect を追加したら、`DEPENDENCY_REQUIRED_KEYS` の表を更新します。

### `E_UNKNOWN_CARD_TYPE`

`card_type`, `type`, `types`, `card_types` に未知の card type 値がある場合は **error**（warning ではない）です。filter の `card_type` 誤記（例: `creachure`）はロードエラーにならず「候補が空＝何も起きない」になるため、ここで早期に弾きます。

有効値は `effects/composition/card_predicates.py` の `CARD_TYPE_NAMES` に `any` / `element` / `non_creature` を加えたものです。新しいカードタイプを正式追加するなら `CARD_TYPE_NAMES` 側を更新します。

## レビューで撤去したチェック

初版（Codex 実装）にはカードテキストを走査する 2 つのヒューリスティック warning がありました。実データ（DM26-RP1, 90 枚）で検出した内容を 1 件ずつ精査した結果、**実問題は 0 件・誤検出のみ**だったため撤去しました。

- **`W_CONNECTOR_DEPENDENCY`**（撤去）: 「`その後`/`then` などの語があるのに後続 effect に `connector` が無い」を警告していた。しかし `PackagedEffect` の既定接続は `after`（前の効果と独立して必ず実行）で、独立した逐次効果には connector 不要。effect 間の本当のデータ依存は `store_as` / `source` / `count_key` / `{"ref": ...}` で表現されており、これらがあれば connector は要らない。`connector: "then"` が要るのは「前の任意効果がスキップされたら後続もスキップ」という狭いケースだけで、自然言語の逐次表現からは判別できないため、誤検出（14/14 件）にしかならなかった。
- **`W_OPTIONAL_TEXT_MISMATCH`**（撤去）: 「`してもよい`/`〜まで` の語があるのに optional / 上限キーが無い」を警告していた。しかしカードの任意性・上限は構造的に表現される（任意ドロー= `max_amount`+`prompt`、「N体まで選ぶ」= `count`+`optional`、「コストN以下」= `filter.cost.lte`、キーワード/常在ルールの任意性= rule 側）。ラベルや `effect_texts_ja` の文言からこれらへ対応付けることはできず、誤検出（11/11 件）にしかならなかった。

教訓: 任意性・依存は **構造化フィールド**に表れる。warning はキーの有無・別名・未知の値といった構造的事実に限定し、自然言語ラベルの解釈で挙動を推測しない。将来この種の検査を足すなら、テキストではなく構造（例: 「effect が optional 不可なのにテキストが任意を要求」を構造モデルで判定）で行う。

## テスト

```powershell
python -m unittest tests.card_db_tests.test_validation_warnings
python tools/card_db_cli.py --card-dir data/impl_cards validate
```

`tests/card_db_tests/test_validation_warnings.py` には各 warning code の検出テストに加え、撤去した 2 チェックの誤検出パターン（`その後` を含む独立効果・`max_amount` による任意ドロー）が warning を出さないことを確認する回帰ガードがあります。
