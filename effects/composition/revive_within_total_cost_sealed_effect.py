"""コスト合計の上限内で、自分の墓地などからクリーチャーを「封印を1つずつ付けて」出す効果。

《不明な不透明 メモッタ》専用の特殊実装。通常の踏み倒し（召喚扱い）とは異なり、
封印を付けながら出すため、出すクリーチャー自身の「出た時」など
[出ることによって起こる効果]は無視される（ルール上、封印されたクリーチャーは
自身の能力が休止する）。

実装上の要点:
  - 封印されたクリーチャーは「無視される」ため、出したクリーチャー自身の cip だけでなく、
    他のカードの「自分のクリーチャーが出た時」等の登場誘発も発揮されない。これを満たすため、
    バトルゾーンへ出す move では `publish_battle_enter=False` を指定し、BattleZoneEnterEvent
    （= 全ての「出た時」誘発の発生源）を発行しない。当リポジトリの「出た時」系トリガーは
    すべて enter_battle（BattleZoneEnterEvent）を購読しており、zone_change で battle 入場を
    見るカードは存在しないため、これで本人・他者の登場誘発をまとめて止められる。
  - publish_battle_enter を抑止すると enter 時の register_abilities も走らないが、能力購読は
    ゲーム開始時（setup_manager）に全カードへ一括登録され以後解除されない設計なので、墓地由来の
    カードも購読済み。封印中は is_ignored_by_seal ガードで休止し、解除後に働くため手動登録は不要。
  - 出す直前に対象を `is_ignored_by_seal = True` にしておき、ZoneChangeEvent 経由の本人誘発も
    休止させる（安全側）。封印カードはこの後で実際に付ける。
  - タップイン等の[状態定義効果]は CardMover の ZoneChangeEvent 経由で自動適用される
    ため、ここでは特別な処理を行わない（封印された状態のままタップして出る）。
  - 山札が尽きるなどして封印を実際に付けられなかった場合は、ignored フラグを戻して
    通常のクリーチャーとして扱う。
"""

from core.card_filter_evaluator import CardFilterEvaluator
from effects.base.base_effect import BaseEffect
from effects.composition.card_predicates import creature_cost
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class ReviveWithinTotalCostSealedEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
        from_zones,
        filter_spec,
        max_count,
        max_total_cost,
        seal_amount=1,
        summoning_sick=True,
        prompt=None,
        source_card=None,
        store_as=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.from_zones = from_zones or ["graveyard"]
        self.filter_spec = filter_spec or {"card_type": "creature"}
        self.max_count = max_count
        self.max_total_cost = max_total_cost
        self.seal_amount = int(seal_amount)
        self.summoning_sick = summoning_sick
        self.prompt = prompt
        self.source_card = source_card
        self.store_as = store_as

    def resolve(self):
        zone_of = self._candidate_zones()
        chosen = self._select(zone_of)

        revived = []
        for card in chosen:
            if self._revive_with_seal(card, zone_of[card]):
                revived.append(card)

        if self.store_as:
            self.package_context[self.store_as] = revived

        return bool(revived)

    def _select(self, zone_of):
        chosen = []
        total = 0
        while len(chosen) < self.max_count:
            selectable = [
                card
                for card in zone_of
                if card not in chosen
                and total + creature_cost(card) <= self.max_total_cost
            ]
            if not selectable:
                break

            pick = self.game.target_selector.select(
                self.player,
                selectable,
                prompt=self.prompt
                or "封印を付けて出すクリーチャーを選ぶ（コスト合計上限内）",
                can_skip=True,
            )
            if pick is None:
                break

            chosen.append(pick)
            total += creature_cost(pick)

        return chosen

    def _candidate_zones(self):
        evaluator = CardFilterEvaluator(self.game)
        context = {
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
        }
        zone_of = {}
        for zone_name in self.from_zones:
            zone = parse_zone(zone_name)
            for card in list(self.player.get_zone(zone).cards):
                if evaluator.matches(card, self.filter_spec, context):
                    zone_of[card] = zone
        return zone_of

    def _revive_with_seal(self, card, from_zone):
        # 入場イベントより前に「封印されている」とみなさせ、ZoneChangeEvent 経由の
        # 自身の誘発を休止させる（安全側）。封印カードはこの後で付ける。
        card.is_ignored_by_seal = True

        # publish_battle_enter=False で BattleZoneEnterEvent を発行しない。これにより
        # 出したクリーチャー自身の cip も、他カードの「クリーチャーが出た時」誘発も
        # 発揮されない（封印されたクリーチャーは無視されるため）。
        moved = self.game.card_mover.move(
            card=card,
            owner=self.player,
            from_zone=from_zone,
            to_zone=ZoneType.BATTLE,
            reason="revive_within_total_cost_sealed",
            publish_battle_enter=False,
        )
        if not moved:
            card.is_ignored_by_seal = False
            return False

        card.summoning_sick = bool(self.summoning_sick)

        attached = self.game.seal_manager.attach_seals(
            [card],
            amount=self.seal_amount,
            player=self.player,
        )
        if not attached:
            # 封印を付けられなかった場合は通常のクリーチャーとして扱う。
            card.is_ignored_by_seal = False

        return True
