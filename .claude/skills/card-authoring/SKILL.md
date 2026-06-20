---
name: card-authoring
description: DMSIM でカード（クリーチャー/呪文/ツインパクト/城/クロスギア）を JSON で追加・修正するときの手順・ファイル配置・v2 能力フォーマット・validate と owner の落とし穴・テスト観点。「カードを実装/追加/修正」「能力を組む」「○○を作って」「validate が落ちる」「CardTestHarness」等で参照する。
---

# カード実装

新規カードは原則 Python クラスを作らず、JSON 定義と既存 Ability/Effect の組み合わせで追加する。
深掘りは docs/ を参照：能力の書き方は `docs/JSON_SPEC.md`、ハマりどころは `docs/CAVEATS.md` と `docs/imp_tips.md`（実装中に得た知見はここへ追記）、置き場所の判断は `docs/PROJECT_STRUCTURE.md`。

## 手順

1. `data/impl_cards/<セット>.json` にカード定義を追加
2. `data/impl_card_metadata/<同名>.json` に日本語メタデータを追加（ローダが同 `id` へ自動マージ）
3. `python tools/card_db_cli.py --card-dir data/impl_cards validate` で検証
4. `tests/ut/<収録弾>/test_<カード>.py` にユニットテストを書いて実行（収録弾フォルダの分類は「テスト」節を参照）

似た能力の既存カードを `data/impl_cards/DM26-RP1.json` から探して流用するのが最速。ただしコピー元の `to_zone` / `filter` の値を消し忘れない（誤って別ゾーンへ送る事故が多い）。

## ファイル配置

| 種類 | 置き場所 |
|---|---|
| 実カード本体 | `data/impl_cards/<初出弾・商品>.json` |
| 日本語メタデータ | `data/impl_card_metadata/<同名ファイル>.json` |
| テスト専用カード | `tmp_cards/*.json` または `data/cards/test_catalog.json` |
| デッキリスト | `data/decks/*.json` |

カードIDは `namespace.name` 形式（例 `dm26-rp1.R.25/77`、`test.vanilla`）。型番IDには `deck_alias`（DB内一意・英数字スネーク）を併用。ファイルは `cards` キー直下に ID をキーとした dict を置く。

## 能力（v2 グループ形式のみ）

`abilities` は必ず v2 グループ形式。**非空の legacy リスト形式はロードエラー**になる。バニラは `"abilities": {}` か `[]`。

```json
"abilities": {
  "keyword": ["blocker", "w_breaker"],
  "triggered": [
    {
      "ability_id": "sample_enter_draw",
      "trigger": { "type": "enter_battle", "card": { "ref": "source" } },
      "effects": [ { "effect_id": "draw", "amount": 1 } ]
    }
  ]
}
```

グループ: `keyword` / `static` / `triggered` / `activated` / `replacement`。DM26-RP1 系は **全 spec に `ability_id` 必須**。

kind 別の最低キー:
- `creature`: `kind`, `name`/`name_ja`, `cost`, `civilizations`, `power`, `race`, `abilities`
- `spell`: `kind`, `name`/`name_ja`, `cost`, `civilizations`, `abilities`, `effects`
- `twinpact`: `creature` 面と `spell` 面をインライン（各面に `id` 不要）
- `castle`: 城。G城は `special_types: ["galaxy"]` を追加
- `cross_gear`: クロスギア

日本語メタデータ（`data/impl_card_metadata/`）の主キー: `name_ja` / `effect_name_ja`（ルビ展開済み・名前参照用）/ `race_ja` / `effect_texts_ja`（能力ごとに配列）。

## 検証

```powershell
python tools/card_db_cli.py --card-dir data/impl_cards validate
python tools/card_db_cli.py --card-dir data/impl_cards make <card_id>
python tools/card_db_cli.py deck data/decks/<deck>.json
```

`validate` は原則 `OK: <枚数> cards` で通す。エラーが出たら、まず自分が触ったカード ID と今回追加した DSL / effect / condition に紐づくものかを確認する。共有 validator を増やした時は既存カードへの波及も見る。

`filter` の `card_type` 誤記（例 `cleature`）はロードエラーにならず「候補が空＝何も起きない」になる。CLI 検証だけで済ませず、**必ずテストで対象が選べること**を確認する。

## DM26-RP1 由来の実装規約

- 構造化 ability spec は `ability_id`、legacy effect は `effect_id`、v2 effect は `type` を使う。`effect_id: "if"` は不可。
- trigger / attempt の zone は `battle` / `mana` / `shield` / `graveyard` / `deck` / `hand` の正規名に寄せる。`mana_zone` などの alias は trigger 照合で外れる。
- 「そうしたら」「こうして」は後続へ `connector: "then"`。「その後」は connector 省略。
- 「引いてもよい」は `optional: true` ではなく `max_amount` と `prompt`。all-or-nothing は v2 `choice`。
- G城の誘発は `active_zones: ["shield"]` + `active_if` の `shield_face_up`。離れた時誘発は `active_zones: "any"`。
- G城や付与元能力では `source` が能力の発生源を指す。イベント対象は `event.card` / `event.attacker` / `event.shield_card` を使う。
- 解決時に盤面を見たい「なら」は ability の `condition` ではなく `type: "if"`。
- ドロー置換は `replace_with.actions: [{"type": "draw"}]`。通常の `draw` effect を置換内で使わない。

## テスト（CardTestHarness）

カード追加・変更時は `tests/ut/` に対応テストを追加して実行。フルスイートはエンジン・レジストリ・解決系など共有部分を触った時だけ。

### テストの配置（収録弾ごとに分類）

`tests/ut/` 直下は肥大化を避けるため、収録弾ごとのサブパッケージに分ける:

| ディレクトリ | 内容 |
|---|---|
| `tests/ut/dm26_rp1/` | DM26-RP1 弾のカードテスト |
| `tests/ut/dm26_rp2/` | DM26-RP2 弾のカードテスト |
| `tests/ut/common/` | 収録弾に依存しない共通メカニクス（G・ストライク／G・ゼロ／城／クロスギア／フィールド等） |

- 新弾は `tests/ut/dm26_rp3/` のように同形式でフォルダを追加し、docstring 付き `__init__.py` を置く（unittest がサブパッケージとして discover できるようにするため）。
- フォルダ名は `<namespace を snake_case 化>`（`dm26-rp1` → `dm26_rp1`）。
- import はすべて絶対パス（`from tests.helpers import ...` 等）なので、配置フォルダに関わらず修正不要。

弾単位でまとめて実行できる:

```powershell
python -m unittest discover tests/ut/dm26_rp2   # 特定弾のみ
python -m unittest discover tests/ut            # ut 全体
```

```python
from card_testing import CardTestHarness, ScriptedChoiceManager

harness = CardTestHarness(card_dir="data/impl_cards")
card = harness.put_hand(harness.create("dm26-rp1.R.99/77"))
harness.summon(card)
harness.expect_one_packaged_effect()
harness.resolve_all_effects()
```

選択固定は `ScriptedChoiceManager().when_prompt_contains("...", chooser)`。共通 chooser/ヘルパーは `tests/helpers.py`（`choose_by_name`, `choose_value`, `choose_none`, `plain_creature`, `put_shield` 等）。

**ゾーン手動配置は先に `card.owner = player` を設定**してから `card.zone = ...` とゾーンの `add` を行う。`put_hand`/`put_battle` は owner を自動設定するが、墓地・シールド・マナへ直接足すヘルパーは漏れやすく、owner 未設定のまま効果が走ると実行時エラー。

### テスト観点チェックリスト

1. validate / make / deck が通る（新規エラーなし）
2. 対象イベントで誘発し、対象外で誘発しない。`active_zones` が正しい（城はシールドゾーン）
3. 1 能力から積まれる Effect 数が期待通り（複合は `PackagedEffect` 1 つ）
4. 解決順（見る→選ぶ→公開→移動→分岐）が正しく `store_as` を後続が参照できる
5. 条件成立時のみ後続が動く。任意効果スキップ時に後続が暴発しない（`connector: "then"`）
6. 移動元・移動先が正しく、残りカードが正しいゾーンへ戻る
7. 未解決 Effect が残らない。無関係カードが動いていない。召喚酔い等の周辺状態を壊していない

## 新規 Python が必要なとき

既存 JSON 部品で表現できない時のみ追加する。優先順位は **JSON → 既存 Effect → Condition → Selector → Effect → Ability**。能力の置き場所:

| 種類 | 場所 |
|---|---|
| キーワード能力 | `abilities/keywords/` + `abilities/registry.py` |
| 誘発型能力 | `abilities/triggered/` |
| 常在型能力 | `abilities/continuous/` |
| 置換効果 | `abilities/replacement/` |
| 状態変化（draw/destroy/bounce/tap 等） | `effects/` |
| 複雑な合成 | `card_db/v2_ability_parser.py` + registry |

新しい部品（効果ID・condition type・置換アクション等）を足したら、`card_db/card_definition_validator.py` への登録、`docs/JSON_SPEC.md` / `docs/imp_tips.md` への追記、テストをセットで行う。
