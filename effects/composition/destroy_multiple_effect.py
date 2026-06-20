"""Destroy a group of cards simultaneously."""

from actions.destroy_multiple_action import DestroyMultipleAction
from core.effect_argument_resolver import EffectArgumentResolver
from effects.base.base_effect import BaseEffect


class DestroyMultipleEffect(BaseEffect):
    """対象カード群を同時に破壊する。

    対象は以下のいずれかで指定する。
      - source: package_context に格納済みのカード（リスト）を参照するキー
      - cards / target: 明示的なカード参照（ref など）

    破壊は DestroyMultipleAction を通じて2フェーズ（試行・置換 → 確定・移動）で
    処理されるため、置換効果や「破壊された時」のトリガーは移動前の盤面全体を
    同時状態として観測できる。
    """

    def __init__(
        self,
        game,
        player,
        source=None,
        cards=None,
        source_card=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.source = source
        self.cards_spec = cards
        self.source_card = source_card
        self.args = EffectArgumentResolver(game)

    def resolve(self):
        targets = self._resolve_targets()
        if not targets:
            return False

        self.game.action_processor.process(
            DestroyMultipleAction(
                self.player,
                targets,
            )
        )
        return True

    def _resolve_targets(self):
        if self.source is not None:
            raw = self.package_context.get(self.source)
            if raw is None:
                return []
            cards = raw if isinstance(raw, list) else [raw]
            return [card for card in cards if card is not None]

        if self.cards_spec is not None:
            context = self.args.context(
                self.player,
                source_card=self.source_card,
                package_context=self.package_context,
            )
            return self.args.cards(
                self.cards_spec,
                context,
            )

        return []
