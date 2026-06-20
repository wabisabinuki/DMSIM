"""
指定された枚数のカードをプレイヤーの山札（Deck）から手札（Hand）へ移動させるドロー効果を処理するクラス。
"""

from effects.base.base_effect import (
    BaseEffect
)

from core.protocols import ZoneContext
from core.ref_resolver import RefResolver
from effects.amount_choice import resolve_effect_amount
from effects.composition.card_predicates import creature_cost


class DrawEffect(
    BaseEffect
):

    def __init__(
        self,
        player,
        amount,
        game: ZoneContext,
        min_amount=None,
        max_amount=None,
        prompt=None,
        optional=False,
    ):

        super().__init__()

        self.player = player
        self.amount = amount
        self.game = game
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.prompt = prompt
        self.optional = optional

    def resolve(self):
        amount = self._resolve_amount()

        if self.optional and amount > 0:
            # 「N枚引いてもよい」: 解決時に確定した枚数 N を上限に 0〜N を選ばせる。
            # max_amount が動的（stored 参照）でも、確定後の値に対して適用できる。
            amount = resolve_effect_amount(
                game=self.game,
                player=self.player,
                amount=amount,
                min_amount=0,
                max_amount=amount,
                prompt=self.prompt or f"何枚引きますか？（最大{amount}）",
            )

        self.player.draw(
            self.game,
            amount,
        )

        print(
            f"{self.player.name} draws "
            f"{amount}"
        )

    def _resolve_amount(self):
        if not isinstance(self.amount, dict):
            return resolve_effect_amount(
                game=self.game,
                player=self.player,
                amount=self.amount,
                min_amount=self.min_amount,
                max_amount=self.max_amount,
                prompt=self.prompt,
            )

        if self.amount.get("from") == "stored":
            key = self.amount["key"]
            value = self.package_context.get(key)

            if value is None:
                return 0

            if self.amount.get("field") is None:
                return resolve_effect_amount(
                    game=self.game,
                    player=self.player,
                    amount=value,
                    min_amount=self.min_amount,
                    max_amount=self.max_amount,
                    prompt=self.prompt,
                )

            if self.amount.get("field") == "creature_cost":
                return resolve_effect_amount(
                    game=self.game,
                    player=self.player,
                    amount=creature_cost(value),
                    min_amount=self.min_amount,
                    max_amount=self.max_amount,
                    prompt=self.prompt,
                )

        if (
            self.amount.get("from") == "source_info"
            or (
                isinstance(self.amount.get("ref"), str)
                and self.amount["ref"].startswith("source_info")
            )
        ):
            amount = RefResolver(
                self.game
            ).resolve(
                self.amount,
                self._ref_context(),
            )
            return resolve_effect_amount(
                game=self.game,
                player=self.player,
                amount=amount,
                min_amount=self.min_amount,
                max_amount=self.max_amount,
                prompt=self.prompt,
            )

        raise ValueError(f"Unsupported draw amount: {self.amount}")

    def _ref_context(
        self,
    ):
        event = None
        condition_context = getattr(
            self,
            "condition_context",
            None,
        )
        if condition_context is not None:
            event = getattr(
                condition_context,
                "event",
                None,
            )

        return {
            "game": self.game,
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
            "source_info": self.source_info,
            "package_context": self.package_context,
            "event": event,
        }
