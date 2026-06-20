# DMSIM

DMSIMは、デュエル・マスターズ風のカードゲームを検証するためのPython製シミュレータです。
プレイヤーの行動、領域移動、誘発能力、置換効果、継続効果、シールド・トリガーなどを小さな部品に分けて実装し、カード定義はJSONで追加できるようにしています。

## できること

- 2人対戦の簡易ゲーム進行
- 召喚、呪文使用、攻撃、ブロック、シールドブレイク
- 誘発能力、常在能力、置換能力、期間付き効果
- ツインパクト、進化クリーチャー、NEOクリーチャー系の検証
- JSONカード定義とデッキ定義の読み込み
- カードDB確認用のCLI補助ツール

## 必要環境

- Python 3.12以上

依存ライブラリは現在ありません。仮想環境を使う場合は、通常のPythonプロジェクトと同じように作成してください。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 実行方法

サンプルデッキを使って、CLI上で簡易ゲームを開始します。

```powershell
python main.py
```

`main.py` は `data/impl_cards/` のカード定義と `data/decks/player1_deck.json`、`data/decks/player2_deck.json` を読み込み、2人分のデッキを作ってターンを進めます。Player1 と Player2 で別々のデッキを使う場合は、デッキJSONをそれぞれ指定します。

```powershell
python main.py --player1-deck data/decks/player1_deck.json --player2-deck data/decks/player2_deck.json
```

## カード定義

カードは原則としてPythonクラスを増やさず、JSONで追加します。

- 実カード定義: `data/impl_cards/*.json`（日本語メタデータは `data/impl_card_metadata/*.json`）
- サンプルカード定義: `data/cards/*.json`
- デッキ定義: `data/decks/*.json`
- カード生成: `card_db/`
- 能力実装: `abilities/`
- 効果実装: `effects/`

カードDBの確認には `tools/card_db_cli.py` を使います。

```powershell
python tools/card_db_cli.py --card-dir data/impl_cards validate
python tools/card_db_cli.py --card-dir data/impl_cards list
python tools/card_db_cli.py --card-dir data/impl_cards show <card_id>
python tools/card_db_cli.py --card-dir data/impl_cards make <card_id>
python tools/card_db_cli.py deck data/decks/player1_deck.json
```

カード追加の詳細は [docs/CARD_AUTHORING.md](docs/CARD_AUTHORING.md) を参照してください。

## カード定義の検証

追加・修正したカード定義は CLI の `validate` で検証できます。

```powershell
python tools/card_db_cli.py --card-dir data/impl_cards validate
```

カード追加時の検証観点は [docs/CARD_AUTHORING.md](docs/CARD_AUTHORING.md) を参照してください。

## ディレクトリ構成

```text
abilities/       カードが持つ能力
actions/         プレイヤーが宣言する行動
card_db/         JSONカード定義の読み込みとカード生成
cards/           カード本体、カード面、利用コンテキスト
cli/             CLI用の選択マネージャ
core/            ゲーム進行、解決、検証、問い合わせ
data/            カード・デッキ定義JSON
docs/            実装説明、利用方法、設計メモ
effects/         解決時にゲーム状態を書き換える効果
events/          イベント型
modifiers/       パワー修正などの継続修飾子
tools/           開発・検証用CLI
ui/              表示・デバッグ出力
zones/           領域型と領域実装
```

より詳しい構成は [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) にあります。

## 実装の見取り図

ゲーム処理は、おおまかに次の流れで進みます。

1. プレイヤーの行動を `actions/` のActionとして表す
2. `core/action_validator.py` で実行可能か確認する
3. `core/action_processor.py` が対応するHandlerへ処理を渡す
4. 領域移動は `core/card_mover.py` が担当する
5. 移動や攻撃などのイベントを `core/event_manager.py` が通知する
6. `core/trigger_manager.py` が誘発能力を検出して効果をキューへ積む
7. `core/game_loop.py` が状態定義処理と効果解決を収束するまで回す

詳しい設計メモは `docs/` 以下に分かれています（索引は [docs/README.md](docs/README.md)）。

- [docs/OVERVIEW.md](docs/OVERVIEW.md) — シミュレーション概要
- [docs/CARD_AUTHORING.md](docs/CARD_AUTHORING.md) — カードの追加方法とテスト
- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) — フォルダ構造
- [docs/JSON_SPEC.md](docs/JSON_SPEC.md) — カード定義JSONの仕様
- [docs/CAVEATS.md](docs/CAVEATS.md) — 詳細な注意点
- [docs/imp_tips.md](docs/imp_tips.md) — 実装Tips

## 開発メモ

- 実装説明や利用方法は `docs/` に追加します。
- テストケースは `tests/` に追加します。
- カード量産では `cards/` に個別カードクラスを増やす前に、JSON定義で表現できるか確認します。
- 新しい能力IDや効果IDを追加した場合は、対応するregistryやfactoryへの登録も忘れずに行います。
