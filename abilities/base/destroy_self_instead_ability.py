"""イベントの身代わりとして自分自身を破壊する置換能力の基底クラス。"""

from abilities.base.replacement_ability import ReplacementAbility
from actions.destroy_action import DestroyAction
from zones.zone_type import ZoneType


class DestroySelfInsteadAbility(ReplacementAbility):
    """対象イベントをキャンセルし、かわりに owner_card を破壊する。

    サブクラスは `applies()` と `confirm_prompt` を定義する
    （例: シールド・セイバー、セイバー：種族）。
    """

    confirm_prompt = "Use this ability?"

    def __init__(
        self,
        owner_card,
        game,
        optional=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.optional = optional

    def replace(
        self,
        event,
    ):
        if self.optional:
            proceed = self.game.choice_manager.select(
                self.owner_card.owner,
                [
                    True,
                    False,
                ],
                prompt=self.confirm_prompt,
            )
            if not proceed:
                return False

        self.game.action_processor.process(
            DestroyAction(
                self.owner_card.owner,
                self.owner_card,
            )
        )
        # 自身の破壊が（置換などで）成立しなかった場合は身代わり不成立。
        if self.owner_card.zone == ZoneType.BATTLE:
            return False

        event.cancelled = True
        return True
