# フォルダ構造

カード定義データとゲームロジックを分離し、能力・効果は分類パッケージ + レジストリで管理する。

## トップレベル

```text
abilities/       カードが持つ能力。分類サブディレクトリ + registry
actions/         プレイヤーが宣言する行動
archive/         移行済み互換ファイルの保管先（通常実行経路から除外）
card_db/         JSONカード定義の読み込みとカード生成（v2 パーサ含む）
card_testing/    CardTestHarness などカードテスト用補助
cards/           カード基底クラスと特殊カード型（個別カードは置かない）
cli/             CLI用の選択マネージャ
core/            ゲーム進行、解決、検証、問い合わせ、DSL評価
data/            実カード・メタデータ・デッキのJSON
docs/            ドキュメント
effects/         解決時にゲーム状態を書き換える効果
events/          イベント型
modifiers/       パワー修正などの継続修飾子
tests/           テスト（分類サブディレクトリ）
tmp_cards/       テスト専用カード定義JSON（フィクスチャ）
tools/           開発・検証用CLI
ui/              表示・デバッグ出力
zones/           領域型と領域実装
```

## data/

```text
data/
  impl_cards/           実カード定義（例: DM26-RP1.json）
  impl_card_metadata/   実カードの日本語メタデータ（同名ファイルが自動マージされる）
  cards/                テスト用カタログ（test_catalog.json）。CLI の既定ディレクトリ
  decks/                デッキリスト
```

`CardDatabase.load_dir(<dir>)` は `<dir>` 名の `cards` を `card_metadata` に置き換えたディレクトリ（`impl_cards` → `impl_card_metadata`）を自動で読み、同じ `id` のカードへメタデータをマージする。`main.py` は `data/impl_cards` を読む。

## abilities/

```text
abilities/
  base/          Ability基底（継続型、誘発型、置換型）
  keywords/      blocker、speed_attacker、ブレイカー等の能力語
  traits/        公式キーワードではない常在能力（cannot_cast_spells、コスト軽減等）
  triggers/      イベント誘発能力の実装
  replacements/  置換能力の実装
  auras/         周囲へ常在的に影響する能力
  cross_gear/    クロスギア連動能力
  v2/            構造化v2の実行系（JsonTriggeredAbility、trigger_matcher、spec_schema、event_map）
  registry.py    ability id → Ability インスタンスの登録表（ABILITY_BUILDERS）
```

## effects/

```text
effects/
  base/          Effect基底、期間付きEffect基底
  composition/   packaged、select_then、once_per_turn 等の複合・制御系
  modifiers/     パワー修正など修飾子を付与する効果
  zones/         draw、discard、move_card など領域移動系
  combat/        tap/untap、一時能力付与、戦闘制限など
  cross_gear/    クロス関連効果
  registry.py    legacy effect id → Effect の登録表（EFFECT_BUILDERS）
  effect_factory.py  v2 effect type → Effect の組み立て（EffectFactory.BUILDERS）
  effect_context.py  store_as / ref の保存・解決
```

## tests/

```text
tests/
  ut/                カード別の実装確認（1カード=1ファイル目安）
  ability_tests/     能力仕様
  effect_tests/      効果の単体・組み合わせ
  card_db_tests/     カードDB、JSON authoring、メタデータ、deck alias
  card_model_tests/  カード型、進化/NEO などカードモデル
  core_tests/        ターン処理、イベント、優先度などゲーム基盤
  ui_tests/          CLI表示
  package_tests/     パッケージ export
  helpers.py         共通 chooser / カード生成ヘルパー
```

ディレクトリ名は実装パッケージを shadow しないよう `_tests` suffix を付ける。

## コードを置く場所の判断基準

| やりたいこと | 置く場所 |
|---|---|
| カードを追加する | `data/impl_cards/*.json`（テスト用は `tmp_cards/`） |
| 既存能力を組み合わせる | カードJSONの `abilities`（[JSON_SPEC.md](JSON_SPEC.md)） |
| キーワード能力を追加する | `abilities/keywords/`（公式語）または `abilities/traits/`（非公式の常在能力）+ `abilities/registry.py` に登録 |
| 誘発能力を追加する | まず v2 `triggered` の JSON で表現できないか確認。無理なら `abilities/triggers/` |
| 置換効果を追加する | v2 `replacement` で表現できないか確認。無理なら `abilities/replacements/` |
| 単発効果を追加する | `effects/` の該当カテゴリ + `effects/registry.py`（legacy id）または `effects/effect_factory.py`（v2 type）に登録 |
| 条件タイプを追加する | `core/condition_registry.py` + `core/condition_evaluator.py`（手順は [JSON_SPEC.md](JSON_SPEC.md)） |
| ref 参照を追加する | `core/ref_resolver.py` の `ROOT_RESOLVERS` / `PART_RESOLVERS` |
| カード1枚だけが特殊すぎる | 最後の手段として `cards/` に専用クラス。同じ挙動が2枚目に出たら抽出する |

外部コードから能力・効果クラスを使う場合は package root から import する。

```python
from abilities import SpeedAttackerAbility
from effects import DrawEffect, build_effects
```
