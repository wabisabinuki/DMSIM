"""Count stored cards matching a filter and store the result."""

from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.base.base_effect import BaseEffect


class CountMatchingEffect(BaseEffect):
    """package_context[source]に格納されたカードの中でfilter_specに
    一致するカードの枚数を数え、package_context[store_as]に格納する。

    source が単一カードでも複数カードのリストでも正しく動作する。
    key が未設定の場合はカウント 0 を格納する。
    """

    def __init__(
        self,
        game,
        player,
        source,
        filter_spec,
        store_as,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.source = source
        self.filter_spec = filter_spec or {}
        self.store_as = store_as

    def resolve(self):
        raw = self.package_context.get(self.source)

        if raw is None:
            cards = []
        elif isinstance(raw, list):
            cards = raw
        else:
            cards = [raw]

        context = {
            "player": self.player,
            "source_card": self.source_card,
        }

        count = sum(
            1
            for card in cards
            if matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.filter_spec,
                context=context,
            )
        )
        self.package_context[self.store_as] = count
        return True
