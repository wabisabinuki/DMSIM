"""超次元ゾーンからの登場を予約する遅延誘発効果。

「次の相手のターンのはじめに、相手はそのクリーチャーを超次元ゾーンから出す」を、
ニンジャ・ストライクの山札戻し（NinjaStrikeReturnEffect）と同じ idiom で実装する。
解決時に TurnStartEvent を購読し、対象プレイヤーの次のターン開始時に1度だけ
そのクリーチャーをバトルゾーンへ出して購読を解除する。発生源が離れても独立に解決する。

進化クリーチャーの場合は「出す」時点で進化元を改めて選び直す。進化元がなければ
出せず、超次元ゾーンに残したまま効果は解決済みとして扱う（進化元なしの進化
クリーチャーをバトルゾーンへ出してはいけない）。
"""

from core.evolution_support import (
    evolution_source_candidates,
    requires_evolution_source,
    source_count_for,
    stack_evolution_sources,
)
from effects.base.base_effect import BaseEffect
from events.turn_event import TurnStartEvent
from zones.zone_type import ZoneType


class SuperDimensionReleaseEffect(BaseEffect):

    def __init__(
        self,
        game,
        card,
        owner,
        source_card=None,
    ):
        super().__init__()
        self.game = game
        self.card = card
        self.release_owner = owner
        self.source_card = source_card
        self.is_active = False

    def resolve(self):
        self.game.event_manager.subscribe(
            TurnStartEvent,
            self.on_turn_start,
        )
        self.is_active = True
        return True

    def on_turn_start(self, event):
        if not self.is_active:
            return

        if getattr(event, "player", None) is not self.release_owner:
            return

        self._release()
        self._deactivate()

    def _release(self):
        card = self.card
        # 解決時点で対象が超次元ゾーンにいなければ何もしない。
        if card.zone != ZoneType.SUPER_DIMENSION:
            return

        needs_source = requires_evolution_source(card)

        evolution_source = None
        if needs_source:
            evolution_source = self._choose_evolution_source(card)
            # その時点で進化元を選べなければ出せない（効果は解決済み扱い）。
            if evolution_source is None:
                return

        moved = self.game.card_mover.move(
            card=card,
            owner=self.release_owner,
            from_zone=ZoneType.SUPER_DIMENSION,
            to_zone=ZoneType.BATTLE,
            reason="super_dimension_release",
            # 進化元は出した後に重ねるため、入場イベントはその後で発行する。
            publish_battle_enter=not needs_source,
        )

        if not (moved and card.zone == ZoneType.BATTLE):
            return

        if evolution_source is not None:
            stack_evolution_sources(
                self.release_owner,
                card,
                evolution_source,
            )
            self.game.card_mover.publish_battle_enter(
                card=card,
                owner=self.release_owner,
                from_zone=ZoneType.SUPER_DIMENSION,
                reason="super_dimension_release",
            )

        # 出たターン扱い（召喚酔いのまま）。
        card.summoning_sick = True
        card.summon_turn = self.game.state.turn

    def _choose_evolution_source(self, card):
        candidates = evolution_source_candidates(
            self.release_owner,
            card,
        )
        source_count = source_count_for(card)
        if len(candidates) < source_count:
            return None

        prompt = f"Choose evolution source for {card.name}"
        if source_count != 1:
            return self.game.choice_manager.select(
                self.release_owner,
                candidates,
                prompt=prompt,
                min_count=source_count,
                max_count=source_count,
            )

        return self.game.choice_manager.select(
            self.release_owner,
            candidates,
            prompt=prompt,
        )

    def _deactivate(self):
        if not self.is_active:
            return

        self.game.event_manager.unsubscribe(
            TurnStartEvent,
            self.on_turn_start,
        )
        self.is_active = False

    def __str__(self):
        return (
            "SuperDimensionReleaseEffect("
            f"{getattr(self.card, 'name', self.card)})"
        )
