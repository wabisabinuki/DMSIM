"""パワー・ガチンコ・ジャッジ効果（PowerGachinkoJudgeEffect）。

自分と相手は自身の山札の上から1枚を表向きにし、それを山札の下に置く。
そのカードのパワーが相手以上なら自分が勝つ（パワーを持たないカードは0扱い）。
`optional` が真なら「してもよい」（実行可否を確認）。勝敗に応じて `on_win` /
`on_lose` の効果列を解決する。`repeat_until_lose` が真なら、勝ち続ける限り
（または中止するまで）繰り返す（鬼丸「V」型）。
"""

from effects.base.base_effect import BaseEffect
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


def _card_power(card):
    if card is None:
        return 0
    getter = getattr(card, "get_current_power", None)
    if callable(getter):
        try:
            value = getter()
        except Exception:
            value = getattr(card, "power", 0)
    else:
        value = getattr(card, "power", 0)
    return int(value) if value is not None else 0


class PowerGachinkoJudgeEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
        on_win=None,
        on_lose=None,
        optional=False,
        prompt=None,
        repeat_until_lose=False,
        source_card=None,
        store_own_as=None,
        store_opponent_as=None,
        defer_own_bottom_on_win=False,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.on_win_specs = on_win or []
        self.on_lose_specs = on_lose or []
        self.optional = optional
        self.prompt = prompt or "パワー・ガチンコ・ジャッジをしますか？"
        self.repeat_until_lose = repeat_until_lose
        self.source_card = source_card
        self.store_own_as = store_own_as
        self.store_opponent_as = store_opponent_as
        self.defer_own_bottom_on_win = defer_own_bottom_on_win

    def resolve(self):
        attempted = False
        while True:
            if self.optional and not self._confirm():
                break

            opponent = self.game.query.get_opponent(self.player)
            won, own_card, opponent_card = self._run_judge(opponent)
            attempted = True
            self._store_revealed(own_card, opponent_card)

            specs = self.on_win_specs if won else self.on_lose_specs

            if not (won and self.defer_own_bottom_on_win):
                self._put_revealed_on_bottom(self.player, own_card)
            self._put_revealed_on_bottom(opponent, opponent_card)

            self._resolve_branch(specs)

            if won and self.defer_own_bottom_on_win:
                self._put_revealed_on_bottom(self.player, own_card)

            if not (self.repeat_until_lose and won):
                break

        return attempted

    def _confirm(self):
        return bool(
            self.game.choice_manager.select(
                self.player,
                [True, False],
                prompt=self.prompt,
            )
        )

    def _run_judge(self, opponent):
        own_card, own_power = self._reveal_top(self.player)
        opp_card, opp_power = self._reveal_top(opponent)
        won = own_power >= opp_power
        self._log_judge_result(
            opponent,
            own_card,
            own_power,
            opp_card,
            opp_power,
            won,
        )
        return won, own_card, opp_card

    def _reveal_top(self, player):
        cards = player.deck.cards
        if not cards:
            return None, 0

        top = cards[0]
        top.deck_face_up = True
        power = _card_power(top)
        return top, power

    def _put_revealed_on_bottom(self, player, card):
        if card is None:
            return

        card.deck_face_up = False

        if getattr(card, "zone", None) != ZoneType.DECK:
            return

        if getattr(card, "owner", player) is not player:
            return

        if card not in player.deck.cards:
            return

        player.deck.remove(card)
        player.deck.add(card)

    def _store_revealed(self, own_card, opponent_card):
        if self.store_own_as:
            self.package_context[self.store_own_as] = own_card

        if self.store_opponent_as:
            self.package_context[self.store_opponent_as] = opponent_card

    def _log_judge_result(
        self,
        opponent,
        own_card,
        own_power,
        opponent_card,
        opponent_power,
        won,
    ):

        winner = self.player if won else opponent
        print(
            "ガチンコジャッジ: "
            f"{self.player.name}={self._revealed_label(own_card, own_power)} | "
            f"{opponent.name}={self._revealed_label(opponent_card, opponent_power)} | "
            f"{winner.name}の勝ち"
        )

    def _revealed_label(
        self,
        card,
        power,
    ):

        if card is None:
            return "山札なし (0)"

        return (
            f"{format_card_name(card, mark_battle_label=False)} "
            f"({power})"
        )

    def _resolve_branch(self, specs):
        if not specs:
            return

        # EffectFactory 経由で組むことで、registry の effect_id と v2 の type
        # （例: destroy card ref source）の両方を on_win / on_lose に書ける。
        from effects.effect_factory import EffectFactory

        effects = EffectFactory(self.game).build_many(
            specs,
            self.player,
            source_card=self.source_card,
        )
        for effect in effects:
            effect.package_context = self.package_context
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.trigger_snapshot = self.trigger_snapshot
            effect.resolve()
