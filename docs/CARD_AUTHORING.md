# カードの追加方法

新しいカードは原則として Python クラスを作らず、JSON 定義だけで追加する。能力の書き方（JSON の仕様）は [JSON_SPEC.md](JSON_SPEC.md)、ハマりどころは [CAVEATS.md](CAVEATS.md) と [imp_tips.md](imp_tips.md) を参照。

## 手順の全体像

1. `data/impl_cards/<セット>.json` にカード定義を追加する
2. `data/impl_card_metadata/<セット>.json` に日本語メタデータを追加する
3. `python tools/card_db_cli.py --card-dir data/impl_cards validate` で検証する
4. `tests/ut/test_<カード>.py` にユニットテストを書き、実行する

## 1. ファイルの置き場所

| 種類 | 置き場所 |
|---|---|
| 実カード本体 | `data/impl_cards/<初出弾・商品>.json` |
| 実カードの日本語メタデータ | `data/impl_card_metadata/<同名ファイル>.json` |
| テスト専用カード | `tmp_cards/*.json`（または `data/cards/test_catalog.json`） |
| デッキリスト | `data/decks/*.json` |

ファイルは初出弾・商品・プロモ配布単位で分ける。カードIDは `namespace.name` 形式（例: `dm26-rp1.R.25/77`、`test.vanilla`）。デッキや CLI から参照する識別子もカードIDに統一する。

カード定義ファイルは `cards` キーの下にカードIDをキーとした dict を置く形式で書く。

```json
{
  "cards": {
    "dm26-rp1.R.99/77": {
      "name_ja": "サンプル・クリーチャー",
      "kind": "creature",
      "cost": 3,
      "civilizations": ["water"],
      "power": 2000,
      "abilities": {}
    }
  }
}
```

## 2. カード本体を書く

最低限必要なキーは kind ごとに異なる。

- `creature`: `kind`, `name_ja`, `cost`, `civilizations`, `power`, `abilities`（実カードの `race_ja` は metadata に書く）
- `spell`: `kind`, `name_ja`, `cost`, `civilizations`, `abilities`, `effects`
- `twinpact`: `creature` 面と `spell` 面をインラインで定義（各面に `id` は不要）
- `castle`: 城。G城は `special_types: ["galaxy"]` を追加
- `cross_gear`: クロスギア

能力がないバニラは `"abilities": {}`（空 dict）または `[]`（空リスト）。**非空のリスト形式（legacy 形式）はロードエラーになる。** 能力は必ず v2 グループ形式で書く。

```json
"abilities": {
  "keyword": ["blocker", "w_breaker"],
  "triggered": [
    {
      "ability_id": "sample_enter_draw",
      "trigger": { "type": "enter_battle", "card": { "ref": "source" } },
      "effects": [
        { "effect_id": "draw", "amount": 1 }
      ]
    }
  ]
}
```

実装済みカード（`data/impl_cards/DM26-RP1.json`）から似た能力のカードを探して流用するのが早い。ただしコピー元の `to_zone` や `filter` の値を消し忘れないこと（[imp_tips.md](imp_tips.md) 参照）。

## 3. 日本語メタデータを書く

カード本体にはゲーム処理に必要な情報と、可読性のための `name_ja` を置く。`data/impl_card_metadata/` にも `name_ja` を含め、効果名・種族・日本語テキストと一緒に管理する。ローダが同じ `id` のカードへ自動マージする。

```json
{
  "cards": {
    "dm26-rp1.R.99/77": {
      "name_ja": "サンプル・クリーチャー",
      "effect_name_ja": "サンプルクリーチャー",
      "race_ja": "リキッド・ピープル",
      "effect_texts_ja": [
        "このクリーチャーが出た時、カードを1枚引く。"
      ]
    }
  }
}
```

- `name_ja`: 表示用の日本語名。
- `effect_name_ja`: 名前参照効果用のルビ展開済み名（表示には使わない）。
- `race_ja`: 日本語種族（クリーチャーのみ。配列可）。
- `effect_texts_ja`: 日本語効果テキスト。能力ごとに分けて配列にする。
- ツインパクトは各面にも同じキーを書ける。

## 4. 検証する

```powershell
python tools/card_db_cli.py --card-dir data/impl_cards validate
python tools/card_db_cli.py --card-dir data/impl_cards make <card_id>
python tools/card_db_cli.py deck data/decks/<deck>.json   # デッキに入れる場合
```

`validate` で JSON 全体を検証し、`make` で対象カードの型・能力・メタデータが期待通り生成されるか確認する。`--card-dir`（サブコマンドの前に置く）省略時は `data/cards`（テストカタログ）を読む。

`validate` の warning は「即失敗」ではなくレビュー対象の合図。warning code の意味、典型的な修正、実データでの検出状況は [CARD_JSON_VALIDATION_WARNINGS.md](CARD_JSON_VALIDATION_WARNINGS.md) を参照する。

filter の `card_type` 誤記（例: `cleature`）はロードエラーにならず「候補が空＝何も起きない」になるため、CLI 検証だけで済ませず必ずテストで対象が選べることを確認する。

## 5. テストを書く

カードを追加・変更したら `tests/ut/` に対応するユニットテストを追加し、そのテストを実行する。フルテストはエンジン・レジストリ・解決系など共有部分を触った時だけ実行する。

```powershell
python -m unittest tests.ut.test_dm26_rp1_r25_77   # 単一ファイル
python -m unittest discover tests                   # フルスイート（重要変更時のみ）
```

`CardTestHarness` で 2 人対戦の最小環境・カードDB・選択処理・召喚・効果解決をまとめて扱える。

```python
from card_testing import CardTestHarness, ScriptedChoiceManager

harness = CardTestHarness(card_dir="data/impl_cards")
card = harness.put_hand(harness.create("dm26-rp1.R.99/77"))
harness.summon(card)
harness.expect_one_packaged_effect()
harness.resolve_all_effects()
```

選択を固定する場合は `ScriptedChoiceManager` にプロンプト単位の選択関数を差し込む。共通 chooser は `tests/helpers.py`（`choose_by_name`, `choose_value`, `choose_none`, `plain_creature`, `put_shield` 等）にある。

```python
choices = ScriptedChoiceManager().when_prompt_contains(
    "return to hand", choose_by_name("Vanilla Test"),
)
harness = CardTestHarness(choice_manager=choices, card_dir="data/impl_cards")
```

ゾーンへ手動配置する場合は **先に `card.owner = player` を設定**してから zone とゾーンの `add` を行う（[imp_tips.md](imp_tips.md)）。

### テストの観点チェックリスト

1. **カードDB**: validate / make / deck が通る。
2. **誘発**: 対象イベントで誘発する。対象外イベントで誘発しない。活動ゾーン（`active_zones`）が正しい。
3. **キュー**: 1 能力から積まれる Effect の数が期待通り（複合効果は `PackagedEffect` が 1 つ）。
4. **解決順**: 見る → 選ぶ → 公開 → 移動 → 条件分岐などの順序が正しく、`store_as` の値を後続が参照できる。
5. **条件分岐**: 条件成立時のみ後続が動く。任意効果をスキップした時に後続が暴発しない（`connector: "then"`）。
6. **領域移動**: 移動元・移動先が正しい。残りカードが正しいゾーンへ戻る。
7. **終了状態**: 未解決 Effect が残らない。期待しないカードが動いていない。召喚酔いなど周辺状態を壊していない。

## 6. 新しい Python 実装が必要な場合

既存の JSON 部品で表現できない時だけコードを追加する。判断基準と置き場所は [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) を参照。新しい部品（効果ID、condition type、static type 等）を追加した場合は、`docs/`（主に [JSON_SPEC.md](JSON_SPEC.md) と [imp_tips.md](imp_tips.md)）への追記とテストをセットで行う。
