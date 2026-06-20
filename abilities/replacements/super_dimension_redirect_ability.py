"""超次元ゾーンへの置換能力（ゾロ・ア・スタート）。

相手のターンに相手のクリーチャーが超次元ゾーン以外から出る時、かわりにそれを
相手の超次元ゾーンに置く（置換効果）。あわせて「次の相手のターンのはじめに出す」
遅延誘発効果（SuperDimensionReleaseEffect）を予約する。遅延誘発は対象と持ち主を
捕捉して TurnStartEvent を購読するため、発生源が離れても独立に解決する。
"""

from abilities.base.replacement_ability import ReplacementAbility
from cards.creature_card import CreatureCard
from effects.zones.super_dimension_release_effect import (
    SuperDimensionReleaseEffect,
)
from events.zone_change_attempt_event import ZoneChangeAttemptEvent
from zones.zone_type import ZoneType


class SuperDimensionRedirectAbility(ReplacementAbility):

    def __init__(
        self,
        owner_card,
        game,
        label=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.replacement_label = label

    def applies(
        self,
        event,
    ):
        if not isinstance(event, ZoneChangeAttemptEvent):
            return False

        # 発生源がバトルゾーンにいる時のみ有効。
        if self.owner_card.zone != ZoneType.BATTLE:
            return False

        if event.to_zone != ZoneType.BATTLE:
            return False

        # 超次元ゾーンから出る移動（次ターンの再登場）には適用しない。
        if event.from_zone == ZoneType.SUPER_DIMENSION:
            return False

        card = event.card
        if not isinstance(card, CreatureCard):
            return False

        controller = self.owner_card.owner
        opponent = self.game.query.get_opponent(controller)
        if opponent is None:
            return False

        # 出るクリーチャーが相手のものであること。
        if event.owner is not opponent:
            return False

        # 相手のターンであること。
        if self.game.state.current_player is not opponent:
            return False

        return True

    def replace(
        self,
        event,
    ):
        card = event.card
        owner = event.owner

        # 置換効果：出るかわりに相手の超次元ゾーンへ置く。
        event.to_zone = ZoneType.SUPER_DIMENSION

        # 遅延誘発効果：次の相手のターンのはじめに、そのクリーチャーを出す。
        release = SuperDimensionReleaseEffect(
            game=self.game,
            card=card,
            owner=owner,
            source_card=self.owner_card,
        )
        release.resolve()
        return True
