"""
複数ゾーンからクリーチャーを1体選んでバトルゾーンに出す効果。
（例：手札または墓地からコスト3以下のクリーチャーを出す）
"""

from cards.twin_pact_card import TwinPactCard
from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from core.pending_cards import visible_cards
from effects.base.base_effect import BaseEffect
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class PutCreatureFromMultiZoneEffect(BaseEffect):
    """複数のゾーンにまたがる候補からクリーチャーを1体選んでバトルゾーンに出す。"""

    def __init__(
        self,
        player,
        game,
        from_zones,
        filter_spec=None,
        optional=True,
        prompt=None,
        summoning_sick=True,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.from_zones = [parse_zone(z) for z in from_zones]
        self.filter_spec = filter_spec or {"card_type": "creature"}
        self.optional = optional
        self.prompt = prompt or "クリーチャーを選んでバトルゾーンに出す"
        self.summoning_sick = summoning_sick

    def can_attempt(self):
        return bool(self._candidates())

    def resolve(self):
        candidates = self._candidates()
        if not candidates:
            return False

        card = self.game.target_selector.select(
            self.player,
            candidates,
            prompt=self.prompt,
            can_skip=self.optional,
        )
        if card is None:
            return False

        if isinstance(card, TwinPactCard):
            card.select_creature_face()

        moved = self.game.card_mover.move(
            card=card,
            owner=self.player,
            from_zone=card.zone,
            to_zone=ZoneType.BATTLE,
            reason="put_creature",
        )
        if moved:
            if getattr(card, "is_evolution", False):
                card.summoning_sick = False
            else:
                card.summoning_sick = bool(self.summoning_sick)
            card.summon_turn = self.game.state.turn

        return moved

    def _candidates(self):
        cards = []
        filter_context = {
            "player": self.player,
            "source_card": self.source_card,
        }
        for zone_type in self.from_zones:
            zone = self.player.get_zone(zone_type)
            for card in visible_cards(zone.cards):
                if matches_card_filter_dsl_or_legacy(
                    self.game,
                    card,
                    self.filter_spec,
                    context=filter_context,
                    usage_type="creature",
                ):
                    cards.append(card)
        return cards
