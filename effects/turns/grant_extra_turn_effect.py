"""指定プレイヤーに追加ターンを与える効果。"""

from effects.base.base_effect import BaseEffect
from effects.zones.zone_effect_utils import resolve_player


class GrantExtraTurnEffect(BaseEffect):
    """「このターンの後に〜のターンを追加する」を表す効果。

    現在のターンが終わった後に、対象プレイヤーのターンを1回挿入する。
    挿入されたターンは正規の手番ローテーションを消費しない（GameState 側で
    処理）。
    """

    def __init__(
        self,
        game,
        player,
        target_player="self",
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.target_player = target_player

    def resolve(self):
        owner = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )
        if owner is None:
            return False

        self.game.state.grant_extra_turn(owner)
        print(f"{owner.name} gains an extra turn")
        return True
