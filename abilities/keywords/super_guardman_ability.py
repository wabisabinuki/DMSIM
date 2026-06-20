"""
スーパーガードマン能力（置換効果）。
自分の他のクリーチャーがバトルする時、かわりにこのクリーチャーをタップして
バトルさせてもよい。

実装: ReplacementAbility として BattleDeclaredEvent（バトル成立の宣言）に
反応する。バトルの参加者（attacker / defender）に自分の他のクリーチャーが
いれば、この「かわりに」差し替える置換効果として、参加者をこのクリーチャーへ
置き換える（差し替え時に自身をタップする。通常の「ガードマン」と異なり、
タップ状態でも肩代わりできる）。

差し替えは BattleDeclaredEvent の時点で行われるため、攻撃をブロックして
成立したバトル（攻撃クリーチャー vs ブロッカー）にも反応する。置換は
ReplacementManager が「同一イベントに1度だけ」適用する。
"""

from abilities.base.replacement_ability import ReplacementAbility
from core.pending_cards import is_card_pending
from events.battle_event import BattleDeclaredEvent
from events.card_state_event import CardTappedEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class SuperGuardmanAbility(ReplacementAbility):
    """スーパーガードマン。バトル成立の宣言に反応してバトルを肩代わりする。"""

    replacement_priority = 0

    def __init__(
        self,
        owner_card,
        game,
        active_if=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.active_if = active_if

    def applies(
        self,
        event,
    ):
        if not isinstance(event, BattleDeclaredEvent):
            return False

        if not self._is_active():
            return False

        return self._substitutable_side(event) is not None

    def replace(
        self,
        event,
    ):
        side = self._substitutable_side(event)
        if side is None:
            return False

        original = getattr(event, side)

        proceed = self.game.choice_manager.select(
            self.owner_card.owner,
            [True, False],
            prompt=(
                f"{format_card_name(original)} のバトルを"
                f"{format_card_name(self.owner_card)}"
                "（スーパーガードマン）で肩代わりしますか？"
            ),
        )
        if not proceed:
            return False

        self._tap_self()
        self._set_side(event, side, self.owner_card)

        print(
            f"{format_card_name(self.owner_card)} guards for "
            f"{format_card_name(original)}"
        )
        return True

    def _substitutable_side(
        self,
        event,
    ):
        """自分が支配する、かつ自分自身ではないバトル参加者の側を返す。

        通常は防御側（自分のクリーチャーが攻撃された）を優先する。
        """

        owner = self.owner_card.owner
        for side in ("defender", "attacker"):
            battler = getattr(event, side, None)
            if (
                battler is not None
                and battler is not self.owner_card
                and getattr(battler, "owner", None) is owner
            ):
                return side

        return None

    def _set_side(
        self,
        event,
        side,
        new_card,
    ):
        setattr(event, side, new_card)
        # _BattleParticipantsEvent では card=attacker, target=defender。
        if side == "attacker":
            event.card = new_card
        else:
            event.target = new_card

    def _tap_self(
        self,
    ):
        if self.owner_card.tapped:
            return

        self.owner_card.tapped = True
        self.game.event_manager.publish(
            CardTappedEvent(
                self.owner_card.owner,
                self.owner_card,
                reason="super_guardman",
            )
        )

    def _is_active(
        self,
    ):
        return (
            self.game is not None
            and self.owner_card.zone == ZoneType.BATTLE
            and not is_card_pending(self.owner_card)
        )

    def __str__(self):
        return "SuperGuardman"
