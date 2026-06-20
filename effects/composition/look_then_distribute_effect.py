"""山札の上から N 枚を見て、複数のゾーンへ振り分ける効果。

「山札の上から3枚を見る。その中から、エレメントを最大1つ出し、1枚をシールド化し、
残りをマナゾーンに置く。」のような分配を表す。``buckets`` を上から順に処理し、各
バケットで条件に合うカードを選んで ``to_zone`` へ動かす。選んだカードは候補から外し、
最後に残ったカードを ``remainder_zone`` へ置く。
"""

from core.card_filter_evaluator import CardFilterEvaluator
from effects.base.base_effect import BaseEffect
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class LookThenDistributeEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
        amount,
        buckets,
        remainder_zone,
        source_card=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.amount = amount
        self.buckets = buckets or []
        self.remainder_zone = remainder_zone
        self.source_card = source_card

    def resolve(self):
        pile = list(self.player.deck.cards[: self.amount])
        if not pile:
            return False

        evaluator = CardFilterEvaluator(self.game)
        context = {
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
        }
        remaining = list(pile)

        for bucket in self.buckets:
            if not remaining:
                break

            to_zone = parse_zone(bucket["to_zone"])
            filter_spec = bucket.get("filter", {})
            optional = bool(bucket.get("optional", False))
            count = int(
                bucket.get(
                    "count",
                    bucket.get("max", 1),
                )
            )
            candidates = [
                card
                for card in remaining
                if evaluator.matches(card, filter_spec, context)
            ]
            if not candidates:
                continue

            for card in self._choose(
                candidates,
                count,
                optional,
                bucket.get("prompt"),
            ):
                if self._move(card, to_zone):
                    remaining.remove(card)

        remainder_zone = parse_zone(self.remainder_zone)
        for card in list(remaining):
            self._move(card, remainder_zone)

        return True

    def _choose(
        self,
        candidates,
        count,
        optional,
        prompt,
    ):
        prompt = prompt or "カードを選ぶ"

        if count <= 1:
            selected = self.game.target_selector.select(
                self.player,
                candidates,
                prompt=prompt,
                auto_choose_single=not optional,
                can_skip=optional,
            )
            return [selected] if selected is not None else []

        return [
            card
            for card in self.game.target_selector.select_multiple(
                self.player,
                candidates,
                prompt=prompt,
                min_count=0 if optional else min(count, len(candidates)),
                max_count=count,
                can_skip=optional,
            )
            if card is not None
        ]

    def _move(
        self,
        card,
        to_zone,
    ):
        kwargs = {}
        if to_zone == ZoneType.SHIELD:
            kwargs["shield_face_up"] = False

        moved = self.game.card_mover.move(
            card=card,
            owner=self.player,
            from_zone=ZoneType.DECK,
            to_zone=to_zone,
            reason="look_then_distribute",
            **kwargs,
        )
        if moved and to_zone == ZoneType.BATTLE:
            card.summoning_sick = True

        return moved
