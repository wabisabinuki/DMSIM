"""山札の上を見てクリーチャーを1体出し、残りをシャッフルして山札の下に置く効果。

「自分の山札の上から N 枚を見る。その中から〔条件〕のクリーチャーを1体出しても
よい。残りをシャッフルして山札の下に置く」をそのまま表す。``filter_spec`` で
出せる候補を限定する（例: 光のコスト9のクリーチャー）。選ばれなかった/条件に
合わないカードは「残り」としてまとめてシャッフルされ、山札の下へ置かれる。
"""

import random

from effects.base.base_effect import BaseEffect
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.pending_cards import visible_cards
from zones.zone_type import ZoneType


class LookTopPutCreatureToBattleEffect(BaseEffect):

    def __init__(
        self,
        player,
        amount,
        game,
        store_as=None,
        optional=True,
        filter_spec=None,
        prompt=None,
        summoning_sick=True,
    ):
        super().__init__()

        self.player = player
        self.amount = amount
        self.game = game
        self.store_as = store_as
        self.optional = optional
        self.filter_spec = filter_spec or {}
        self.prompt = prompt or "Choose a creature to put into the battle zone"
        self.summoning_sick = summoning_sick

    def resolve(self):
        seen = visible_cards(
            self.player.deck.cards
        )[: self.amount]

        if not seen:
            if self.store_as:
                self.package_context[self.store_as] = None
            return False

        candidates = [
            card
            for card in seen
            if self._matches(card)
        ]

        selected = None
        if candidates:
            selected = self.game.target_selector.select(
                self.player,
                candidates,
                prompt=self.prompt,
                can_skip=self.optional,
            )

        if selected is not None:
            moved = self.game.card_mover.move(
                card=selected,
                owner=self.player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.BATTLE,
                reason="look_top_put_creature_to_battle",
            )
            if moved:
                self._on_enter(selected)
                print(
                    f"{self.player.name} put "
                    f"{selected.name} into the battle zone"
                )
            else:
                selected = None

        if self.store_as:
            self.package_context[self.store_as] = selected

        remaining = [
            card
            for card in seen
            if card is not selected
            and card in self.player.deck.cards
        ]
        random.shuffle(remaining)
        for card in remaining:
            self.player.deck.remove(card)
            self.player.deck.add(card)

        return True

    def _on_enter(
        self,
        card,
    ):
        if getattr(
            card,
            "is_evolution",
            False,
        ):
            card.summoning_sick = False
        else:
            card.summoning_sick = bool(self.summoning_sick)

        card.summon_turn = self.game.state.turn

    def _matches(
        self,
        card,
    ):
        if not self.filter_spec:
            return True

        return matches_card_filter_dsl_or_legacy(
            self.game,
            card,
            self.filter_spec,
            context={
                "player": self.player,
                "controller": self.player,
                "source_card": self.source_card,
            },
        )
