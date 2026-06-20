# CLAUDE.md

このファイルは、このリポジトリで Claude Code または Codex が作業する際のガイドラインです。

DMSIM はデュエル・マスターズのカードゲームシミュレータです。カード定義は JSON、ゲームロジックは Python に実装します。**カードごとの Python クラスは作らず**、Ability と Effect を組み合わせて実装します。

## コマンド

```powershell
python main.py                                  # ゲーム起動
python -m unittest discover tests               # 全テスト
python -m unittest tests.ut.test_aqua_hulcus    # 個別テスト

# カードDB（--card-dir はサブコマンドより前。既定 data/cards、実カードは data/impl_cards）
python tools/card_db_cli.py --card-dir data/impl_cards validate
python tools/card_db_cli.py --card-dir data/impl_cards list
python tools/card_db_cli.py --card-dir data/impl_cards show <id>
python tools/card_db_cli.py deck <path>
```

## アーキテクチャ

ゲームループ（安定するまで繰り返す）:

```
Action → Validate → Execute → Zone Change → Event → Trigger → Effect Queue → Resolve → SBA → loop
```

主要サブシステム:

| モジュール | 責務 |
|---|---|
| `core/game_controller.py` | 全体オーケストレータ |
| `core/game_loop.py` | SBA とキュー解決を安定まで回す収束ループ |
| `core/turn_manager.py` | ターン進行（開始・ドロー・マナ・メイン・攻撃・終了） |
| `core/event_manager.py` | Pub/Sub イベントバス |
| `core/trigger_manager.py` | イベントを能力トリガーに対応付けて Effect を積む |
| `core/effect_resolver.py` | 優先順位順の Effect 実行 |
| `core/card_mover.py` | ゾーン移動（3ステップ + 置換処理） |
| `core/state_based_actions.py` | SBA（0パワー破壊など） |
| `core/combat_manager.py` | 攻撃宣言・ブロック・シールドブレイク |
| `core/game_query.py` | 盤面の問い合わせ（合法対象・ゾーン内容など） |
| `card_testing/harness.py` | `CardTestHarness`（カード検証用の軽量環境） |

### ゾーン移動（必ず CardMover 経由・3ステップ）

`card.zone = ...` の直接代入は禁止。`CardMover` が次の順で処理する:

1. `ZoneChangeAttemptEvent` を publish → 置換能力が移動先を差し替えられる
2. 移動を確定（`card.zone` を設定）
3. `ZoneChangeEvent` を publish → ゾーン変化を購読する能力が誘発

複数枚への破壊・移動は1枚ずつ順番に処理せず、Attempt → 置換 → Event の順で同時に扱う。

### 能力システム（`abilities/`）

4種: 誘発型（`TriggeredAbility`）/ 常在型（`ContinuousAbility`）/ 置換（`ReplacementAbility`）/ キーワード（JSON ID から `abilities/registry.py` 経由で登録）。
誘発時に `CardSnapshot` が状態を捕捉し、解決前に `is_same_card()` で発生源が同一かを確認してゴースト効果を防ぐ。

### Effect システム（`effects/`）

Effect は **1つの責務だけ**を持つ離散的な状態変更（draw / destroy / bounce / tap 等）。`draw_and_destroy` のような複合は作らず composition effect で合成する。
DMの優先順位順に実行: ターンプレイヤーのS・トリガー → 非ターンプレイヤーのS・トリガー → ターンプレイヤーの他効果 → 非ターンプレイヤーの他効果。

### Ability と Effect の役割分担

- **Ability** = 発動条件・条件判定・Effect の生成
- **Effect** = 実際の状態変更

### カード定義（JSON）

`card_db/factory.py` が JSON（`data/impl_cards/`、日本語メタデータは `data/impl_card_metadata/` から自動マージ）を解析し、`CreatureCard` / `SpellCard` / `TwinPactCard` / `CastleCard` / `CrossGearCard` を生成。能力は **v2 グループ形式のみ**（`abilities: {keyword/static/triggered/activated/replacement}`、`card_db/v2_ability_parser.py` が解析）。非空の legacy リストはロード時に拒否される。

カードの追加・修正・能力実装の詳細手順（ファイル配置・v2 フォーマット・validate と owner の落とし穴・テスト観点）は **`card-authoring` スキル** (`.claude/skills`) を参照。

## ワークフロー規則

- **会話・出力はすべて日本語**で行う。
- カード実装時は対応する `tests/ut/` の unit test を個別に必ず追加・更新し、そのカードのテストを実行する。
- 既存カードの実装を参考にする。
- **全テストは共通部分（EventManager / EffectResolver / CardMover / CombatManager / registry / parser 等）を変更した時のみ**実行する。カード単体の変更で毎回フルスイートは回さない。
- 作業終了時に短いコミットメッセージを出力する。

## ドキュメント

`docs/`（索引は `docs/README.md`）: `OVERVIEW.md`（エンジン概要）/ `CARD_AUTHORING.md`（追加手順とテスト）/ `PROJECT_STRUCTURE.md`（フォルダ構成）/ `JSON_SPEC.md`（v2 カード JSON 仕様）/ `CAVEATS.md`（仕組みの落とし穴）/ `imp_tips.md`（実装 Tips・学んだら追記）。
