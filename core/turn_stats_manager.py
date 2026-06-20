"""プレイヤーごとの「このターンの行動」を集計するマネージャー。

「このターンにカードをN枚以上引いた」「このターンにクリーチャーではないカードを
実行した」のような per-turn 条件を、効果側（condition `turn_stat`）から参照できる
ようにする。各ターンの開始時（TurnStartEvent）に全プレイヤーの per-turn 集計を
リセットする。``scope: "game"`` で参照する per-game 集計はゲーム中リセットしない
（GameController が新規ゲームごとに本マネージャーを作り直すことでクリアされる）。

集計対象（stat 名）:
  - ``cards_drawn``             … 山札→手札のドロー枚数（per-turn）
  - ``spells_cast``             … 唱えた呪文の数（per-turn）
  - ``non_creature_executed``   … クリーチャーではないカードを実行した回数（per-turn）
  - ``creatures_attacked``      … 自分のクリーチャーが攻撃を宣言した回数（per-turn）
  - ``final_revolutions_used``  … 「ファイナル革命」を使った回数。per-turn と
                                   per-game の両方に加算する（極限は per-game を参照）
"""

from effects import is_creature_card
from events.attack_event import AttackDeclaredEvent
from events.card_executed_event import CardExecutedEvent
from events.final_revolution_event import FinalRevolutionUsedEvent
from events.spell_cast_event import SpellCastEvent
from events.turn_event import TurnStartEvent
from events.zone_change_event import ZoneChangeEvent
from zones.zone_type import ZoneType


DRAW_REASONS = ("draw", "replacement_draw")


class TurnStatsManager:

    def __init__(
        self,
        context,
    ):
        self.context = context
        self._stats = {}
        self._game_stats = {}

        event_manager = context.zones.event_manager
        event_manager.subscribe(
            ZoneChangeEvent,
            self._on_zone_change,
        )
        event_manager.subscribe(
            SpellCastEvent,
            self._on_spell_cast,
        )
        event_manager.subscribe(
            CardExecutedEvent,
            self._on_card_executed,
        )
        event_manager.subscribe(
            AttackDeclaredEvent,
            self._on_attack_declared,
        )
        event_manager.subscribe(
            FinalRevolutionUsedEvent,
            self._on_final_revolution_used,
        )
        event_manager.subscribe(
            TurnStartEvent,
            self._on_turn_start,
        )

    def get(
        self,
        player,
        stat,
    ):
        return self._stats.get(
            player,
            {},
        ).get(stat, 0)

    def get_game(
        self,
        player,
        stat,
    ):
        return self._game_stats.get(
            player,
            {},
        ).get(stat, 0)

    def reset(
        self,
    ):
        # per-turn 集計のみリセットする。per-game 集計（_game_stats）は
        # ゲーム中は維持する。
        self._stats = {}

    def _bump(
        self,
        player,
        stat,
        amount=1,
    ):
        if player is None:
            return

        player_stats = self._stats.setdefault(player, {})
        player_stats[stat] = player_stats.get(stat, 0) + amount

    def _bump_game(
        self,
        player,
        stat,
        amount=1,
    ):
        if player is None:
            return

        player_stats = self._game_stats.setdefault(player, {})
        player_stats[stat] = player_stats.get(stat, 0) + amount

    def _on_zone_change(
        self,
        event,
    ):
        if (
            event.from_zone == ZoneType.DECK
            and event.to_zone == ZoneType.HAND
            and getattr(event, "reason", None) in DRAW_REASONS
        ):
            self._bump(
                getattr(event, "owner", None),
                "cards_drawn",
            )

    def _on_spell_cast(
        self,
        event,
    ):
        player = getattr(event, "player", None)
        self._bump(player, "spells_cast")
        self._bump(player, "non_creature_executed")

    def _on_card_executed(
        self,
        event,
    ):
        card = getattr(event, "card", None)
        if card is None or is_creature_card(card):
            return

        self._bump(
            getattr(event, "player", None),
            "non_creature_executed",
        )

    def _on_attack_declared(
        self,
        event,
    ):
        self._bump(
            getattr(event, "player", None),
            "creatures_attacked",
        )

    def _on_final_revolution_used(
        self,
        event,
    ):
        # 「ファイナル革命」を使うと per-turn / per-game の両方に加算する。
        # ターン参照（ファイナル革命）とゲーム参照（極限ファイナル革命）の
        # どちらの「他のファイナル革命を使ったか」もこの1つのカウントで判定する。
        player = getattr(event, "player", None)
        self._bump(player, "final_revolutions_used")
        self._bump_game(player, "final_revolutions_used")

    def _on_turn_start(
        self,
        event,
    ):
        self.reset()
