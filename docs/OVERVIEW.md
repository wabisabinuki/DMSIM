# シミュレーション概要

DMSIM はデュエル・マスターズの対戦シミュレータ。カード定義は JSON（`data/impl_cards/` ほか）、ゲームロジックはすべて Python に置く。カードごとの Python クラスは作らず、能力・効果は JSON の ID / DSL からレジストリ経由で組み立てる。

## コアゲームループ

```
プレイヤー行動 → 検証 → 実行 → ゾーン移動 → イベント発行 → 誘発 → 効果キュー → 解決 → SBA → 安定するまでループ
```

| モジュール | 責務 |
|---|---|
| `core/game_controller.py` | 最上位のオーケストレータ。全サブシステムを接続する。 |
| `core/game_loop.py` | ルール収束: 状態が安定するまで SBA 適用と効果解決を繰り返す。 |
| `core/turn_manager.py` | ターン進行（開始、ドロー、チャージ、メイン、攻撃、終了）。 |
| `core/action_processor.py` / `ActionValidator` | 行動のルーティングと検証。実行は `core/action_handlers/`。 |
| `core/event_manager.py` | pub/sub イベントバス。 |
| `core/trigger_manager.py` | イベントと誘発能力を照合し、効果をキューへ積む。 |
| `core/effect_resolver.py` | 優先順位付きの効果解決。 |
| `core/card_mover.py` | ゾーン移動と置換効果の適用。 |
| `core/state_based_actions.py` | 状況起因処理（パワー0破壊、要塞喪失城の墓地送り、付与の reconcile 等）。 |
| `core/combat_manager.py` | 攻撃宣言、ブロック、シールドブレイク。 |
| `core/game_query.py` | 状態問い合わせ（合法対象、ゾーン内容等）。 |
| `core/duration_effect_manager.py` | 期間付き修正・一時能力の管理。 |
| `core/condition_evaluator.py` / `core/ref_resolver.py` | JSON DSL の条件評価と参照解決。 |
| `card_testing/harness.py` | `CardTestHarness` — カード検証用の軽量テスト環境。 |

## ゾーン移動（3段階）

すべてのゾーン移動は `CardMover` を通る。

1. `ZoneChangeAttemptEvent` を発行 → 置換能力が移動先を書き換えられる。
2. 移動を確定（`card.zone` を更新）。
3. `ZoneChangeEvent` を発行 → ゾーン移動を監視する誘発能力が反応する。

破壊は `DestroyAttemptEvent` → `DestroyEvent` が先に処理され、置換された場合は `DestroyEvent` を発行しない。

## 効果の解決優先順位

キューの効果はデュエマの処理順で解決する（`docs/CAVEATS.md` も参照）。

1. ターンプレイヤーの S・トリガー由来の効果
2. 非ターンプレイヤーの S・トリガー由来の効果
3. ターンプレイヤーのその他の効果
4. 非ターンプレイヤーのその他の効果

同一グループ内の複数効果は発生元プレイヤーが解決順を選ぶ。`EffectResolver.add_effect()` が `controller` / `is_shield_trigger` をメタ情報として持つ。

## 保留状態（pending）

カードを使う時、または効果でバトルゾーンへ出る時、移動完了までカードは保留状態になる（`core/pending_cards.py`）。保留中のカードは物理的に元のゾーンに残るが、他の効果・対象選択・枚数参照からは見えない。例外として、マナゾーンから使うカード自身はマナ支払いに使える。保留解除時、保留前に付与されていた一時効果・パワー修正は失われる（タップ状態は保持）。

## 能力モデル

カードの `abilities` は構造化 v2 グループ（`keyword` / `static` / `triggered` / `activated` / `replacement`）で書く。詳細は [JSON_SPEC.md](JSON_SPEC.md)。

| グループ | 基底 / 入口 | 内容 |
|---|---|---|
| keyword | `abilities/keywords/`・`abilities/registry.py` | ブロッカー、W・ブレイカー、S・トリガー等の再利用可能な能力語。 |
| static | `card_db/v2_ability_factory.py` → `abilities/traits/` | 常在型のルール修飾（コスト軽減、召喚許可等）。`type` で機構を指定。 |
| triggered | `JsonTriggeredAbility` | イベント誘発。`trigger` DSL とイベント照合（`abilities/v2/trigger_matcher.py`）。 |
| activated | `JsonActivatedAbility` | 起動型。`timing`（ゾーン・ステップ）を満たすとアクション候補を生成。 |
| replacement | `JsonReplacementAbility` | 置換効果。`attempt` を照合し移動先変更やイベントキャンセルを行う。 |

誘発時には **`CardSnapshot`** が発生源カードの状態を記録し、解決前に `is_same_card()` で同一性を確認する。発生源が領域を離れていれば解決しない（`ignore_source_continuity: true` で無効化可能）。

効果（`effects/`）はキューに積まれる離散的な状態変更で、ゾーン系（draw / discard / move 等）、修飾系（パワー修正、ロック）、戦闘系（tap / untap）、複合系（packaged / if / select_then）に分類される。複数効果を 1 つの解決単位として扱う `PackagedEffect` では、サブ効果間に他の効果が割り込まず、`package_context`（`store_as` / `ref`）で値を共有できる。

## 召喚と「出た時」

- `SummonEvent` = 召喚の **呼び出し**（出たことそのものではない）。
- `BattleZoneEnterEvent`（trigger `type: "enter_battle"`）= 実際にバトルゾーンへ出た時。`reason == "summon"` で召喚由来を判定。
- 置換で別ゾーンへ置かれた場合、`SummonEvent` は出るが `BattleZoneEnterEvent` は出ない。
- 「このクリーチャーが出た時」は常に `enter_battle` を使う。

## シールドゾーン

- シールドは「1 枚以上のカードを含むスロット」の一覧（`zones/shield_zone.py`）。重なったカードは 1 シールドとして数え、移動・ブレイクはスロット単位。
- シールド数の参照は `shield_count()` / `zone_count.shield`（スロット数）。
- カードは `shield_face_up` を持ち、表向きシールドを表現できる（城・G城、効果による表向き配置）。
- **シールドチェック**: S・トリガーと G・ストライクは `SHIELD -> HAND` の移動試行で統一的に確認・キューイングされる。宣言は手札に加わる前、解決は加わった後。
- 城は未要塞化シールドに重ねて要塞化、G城は新規の表向きシールドとして置かれる。詳細は [CAVEATS.md](CAVEATS.md)。

## 期間付き効果

「ターン終わりまで」等の一時効果は `DurationEffect` / `EnchantEffect` 基底と `DurationEffectManager` で管理する。期間タイプは `until_end_of_turn` / `until_end_of_opponent_turn` / `until_start_of_controller_turn` 等。ターン進行時に自動でクリーンアップされる。付与対象がゾーンを離れる・保留状態になると効果は失われる（進化元になった場合は進化先へ転送）。

## カードタイプ

`cards/card.py` の `CardType` に全タイプを定義。実装済みの専用クラスはクリーチャー / 呪文 / ツインパクト / 城（G城含む）/ クロスギア。その他（タマシード等）は `GenericCard` のひな形として生成される。エレメント分類は `ELEMENT_CARD_TYPES`、判定は `card.is_element`。

- **ツインパクト**: `TwinPactCard` がクリーチャー面と呪文面（`CardFace`）を保持。「カード全体」（文明は両面の結合）と「使用中の面」（コスト・文明は面ごと）を分離する。
- **城 / G城**: `kind: "castle"`（G城は `special_types: ["galaxy"]`）。バトルゾーンではなくシールドゾーンで機能する。
- **クロスギア**: ジェネレートで単体で出し、コストを再度払ってクリーチャーへクロス。

## 特殊タイプ

`special_types` で表現する: `evolution`（進化）、`neo`（NEO）、`dream`（ドリーム）、`hyper_mode`（ハイパーモード）。

- 進化は `evolution_sources` に進化元を保持し、領域移動時は束ごと動く。進化元条件は keyword `evolution` / `hand_evolution` / `mana_evolution`。
- ハイパーモードは `hyper_power` を基準パワーにし、`active_if: {"type": "source_has_state", "state": "hyper_mode"}` で「ハイパーモード中だけ有効」な能力を書く。`z_rush` はシールドが離れた時に SBA で即時解放する。
- ドリームは同名のドリーム・エレメントを自分のバトルゾーンに重複して出せない。

## CLI 表示

`ui/card_display.py` / `ui/debug_printer.py` が整形する。バトルゾーンの同名カードは `A`〜`D` の識別子付き、進化クリーチャーは `*` 前置と `(source: A > B)` 表示、ツインパクトは使用面を `【】` で囲む、裏向きシールドは番号のみ表示。
