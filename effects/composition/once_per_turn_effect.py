"""「各ターンに1度」をソースカード上のターンマーカーで表現する汎用効果。

実際に効果を使ったときだけカウントを消費させたい場合、効果チェーンを
``once_per_turn_gate`` で始め、実処理が成功した後に ``connector: "then"`` で
``once_per_turn_mark`` を実行する。

- gate (consume=False): まだ使っていなければ True を返す（マーカーは書かない）。
  すでに使用済みなら False を返し、後続の "then" 効果を止める。
- mark (consume=True): マーカーを書き、True を返す。実処理が成功した後にだけ
  到達するため、スキップや対象不在の場合は消費されない。

同じカードに複数の「各ターンに1度」効果がある場合は ``key`` で区別する。
"""

from effects.base.base_effect import BaseEffect


class OncePerTurnEffect(BaseEffect):
    """ソースカードに保持したターンマーカーで「各ターンに1度」を制御する。"""

    MARKER_ATTR = "_once_per_turn_turns"

    def __init__(
        self,
        game,
        key,
        consume,
    ):
        super().__init__()
        self.game = game
        self.key = key
        self.consume = consume

    def resolve(
        self,
    ):
        holder = self.source_card
        if holder is None:
            return False

        turns = getattr(
            holder,
            self.MARKER_ATTR,
            None,
        )
        if turns is None:
            turns = {}
            setattr(
                holder,
                self.MARKER_ATTR,
                turns,
            )

        current_turn = self.game.state.turn

        # すでに今ターン使用済みなら使えない（gate は False で後続を止める）。
        if turns.get(self.key) == current_turn:
            return False

        if self.consume:
            turns[self.key] = current_turn

        return True
