"""Events produced by creature battle resolution.

バトルの流れ（CombatManager.process_battle）:

1. BattleDeclaredEvent … バトル成立の宣言。置換効果を含む
   「バトル中」の常在型能力はここから有効になる。
2. BattleStartEvent … 「バトルする時」の誘発タイミング。
   スレイヤーの判定もこの時点（誘発解決後）の状態で捕捉される。
3. 両者が残っていればバトル実行 → BattleWonEvent / BattleLostEvent
   （同パワーは両者敗北 = BattleLostEvent が両者に発生）
4. 敗者の破壊（ZoneChangeEvent）と誘発の解決
5. BattleEndEvent … 「バトルの後」タイミング。スレイヤーによる破壊は
   このタイミングの直前に CombatManager が実行する。

いずれかのクリーチャーがバトル実行前にバトルゾーンを離れた場合、
バトルは不成立となり BattleEndEvent（バトルの後）は発生しない。
"""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class _BattleParticipantsEvent(BaseEvent):
    """attacker / defender を持つバトルイベントの共通形。

    card には attacker、target には defender を設定し、
    「このクリーチャーがバトルする時」系の self 条件が
    攻撃側・防御側のどちらでも一致するようにする。
    """

    def __init__(
        self,
        player,
        attacker,
        defender,
        battle_id=None,
    ):
        super().__init__()
        self.player = player
        self.card = attacker
        self.attacker = attacker
        self.defender = defender
        self.target = defender
        self.battle_id = battle_id
        # バトル成立の宣言（BattleDeclaredEvent）はスーパーガードマン等の
        # 「バトルする時、かわりに〜」置換効果の対象となる。ReplacementManager
        # はこのフラグで「同一イベントに置換は1度だけ」を制御する。
        self.replaced = False

    def __str__(self):
        return (
            f"{self.__class__.__name__}("
            f"{format_card_name(self.attacker)} "
            f"vs {format_card_name(self.defender)}"
            ")"
        )


class BattleDeclaredEvent(_BattleParticipantsEvent):
    """バトル成立の宣言。バトル中の常在型・置換能力の開始点。"""


class BattleStartEvent(_BattleParticipantsEvent):
    """「バトルする時」の誘発タイミング。"""


class BattleEndEvent(_BattleParticipantsEvent):
    """「バトルの後」タイミング。バトルが実行された時のみ発生する。"""


class BattleWonEvent(BaseEvent):

    def __init__(
        self,
        player,
        winner,
        loser,
    ):
        super().__init__()
        self.player = player
        self.card = winner
        self.winner = winner
        self.loser = loser

    def __str__(self):
        return (
            "BattleWonEvent("
            f"{format_card_name(self.winner)} "
            f"beat {format_card_name(self.loser)}"
            ")"
        )


class BattleLostEvent(BaseEvent):
    """バトルに敗北した。同パワーの相打ちでは両者に発生する。"""

    def __init__(
        self,
        player,
        loser,
        opponent,
    ):
        super().__init__()
        self.player = player
        self.card = loser
        self.loser = loser
        self.opponent = opponent

    def __str__(self):
        return (
            "BattleLostEvent("
            f"{format_card_name(self.loser)} "
            f"lost to {format_card_name(self.opponent)}"
            ")"
        )
