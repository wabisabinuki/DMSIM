# DMSIM ドキュメント

| ドキュメント | 内容 |
|---|---|
| [OVERVIEW.md](OVERVIEW.md) | シミュレーション概要。ゲームループ、イベント、効果解決、ゾーン、カードタイプなどエンジン全体の仕組み。 |
| [CARD_AUTHORING.md](CARD_AUTHORING.md) | カードの追加方法。ファイルの置き場所、定義の書き方、検証、テストまでの手順。 |
| [CARD_JSON_VALIDATION_WARNINGS.md](CARD_JSON_VALIDATION_WARNINGS.md) | カード JSON validator の warning 仕様。warning code、検出条件、レビュー観点、実データ検出状況。 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | フォルダ構造と、新しいコードを置く場所の判断基準。 |
| [JSON_SPEC.md](JSON_SPEC.md) | カード定義 JSON（構造化 v2）の仕様。能力グループ、trigger / condition / filter / ref DSL、効果。 |
| [CAVEATS.md](CAVEATS.md) | 詳細な注意点。イベントの使い分け、シールド・進化・付与などメカニズムごとの落とし穴。 |
| [imp_tips.md](imp_tips.md) | 実装 Tips。カード実装・デバッグで得られた個別の知見の蓄積（随時追記）。 |

読む順番の目安: 初めての人は OVERVIEW → CARD_AUTHORING → JSON_SPEC。
カード実装中に挙動が想定と違う時は CAVEATS と imp_tips を確認する。
`validate` の warning をレビューする時は CARD_JSON_VALIDATION_WARNINGS を確認する。
