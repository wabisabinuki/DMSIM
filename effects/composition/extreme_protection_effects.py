"""極限ファイナル革命などの「継続保護」を表す期間限定効果。

- ``PreventLossEffect``: 期間中、コントローラーはゲームに負けない。勝敗宣言は
  `GameState` が `loss_prevented` を参照して止める。
- ``OpponentEffectSeparationGuard``: 期間中、相手のカードの効果によってコントローラーの
  クリーチャーがバトルゾーンを離れない。バトル・SBA・自分の効果による移動は通常どおり。
  「相手のカードの効果か」は `game.state.current_effect_controller`（解決中の効果のコント
  ローラー、EffectResolver が設定）で判定する。CardMover の zone_change 防止経路が
  コントローラーの ``separation_guards`` を参照する。

どちらも DurationEffectManager が期間を管理し、満了時に登録を外す。
"""

from effects.base.duration_effect import DurationEffect
from effects.composition.card_predicates import is_creature_card
from zones.zone_type import ZoneType


class PreventLossEffect(DurationEffect):

    def __init__(self, game, controller, duration_type, source_card=None):
        super().__init__(source_card, duration_type, game)
        self.controller = controller

    def can_resolve(self, game_state):
        return True

    def resolve(self):
        if self.controller is None:
            return False

        self.controller.loss_prevented = (
            getattr(self.controller, "loss_prevented", 0) + 1
        )
        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(self)
        return True

    def unapply(self):
        if getattr(self.controller, "loss_prevented", 0) > 0:
            self.controller.loss_prevented -= 1
        super().unapply()


class OpponentEffectSeparationGuard(DurationEffect):

    def __init__(self, game, controller, duration_type, source_card=None):
        super().__init__(source_card, duration_type, game)
        self.controller = controller

    def can_resolve(self, game_state):
        return True

    def resolve(self):
        if self.controller is None:
            return False

        guards = getattr(self.controller, "separation_guards", None)
        if guards is None:
            guards = []
            self.controller.separation_guards = guards
        guards.append(self)

        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(self)
        return True

    def unapply(self):
        guards = getattr(self.controller, "separation_guards", [])
        if self in guards:
            guards.remove(self)
        super().unapply()

    def prevents_zone_change(self, event):
        if not self.is_active:
            return False

        if getattr(event, "from_zone", None) != ZoneType.BATTLE:
            return False
        if getattr(event, "to_zone", None) == ZoneType.BATTLE:
            return False

        card = getattr(event, "card", None)
        if not is_creature_card(card):
            return False
        if getattr(card, "owner", None) is not self.controller:
            return False

        # 「相手のカードの効果によって」だけ防ぐ。バトル・SBA・ルール処理
        # （cause is None）と自分の効果（cause is controller）は防がない。
        cause = getattr(
            self.game.state,
            "current_effect_controller",
            None,
        )
        return cause is not None and cause is not self.controller
