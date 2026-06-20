"""Gather every battle-zone creature matching a filter and store the list."""

from core.card_filter_evaluator import CardFilterEvaluator
from effects.base.base_effect import BaseEffect


class GatherMatchingEffect(BaseEffect):
    """指定した候補集合(自分/相手/全体のクリーチャー)から filter_spec に
    一致するカードをすべて集め、package_context[store_as] にリストとして格納する。

    「選ぶ」効果ではないため、選択不可(can't be chosen)の保護は無視して
    バトルゾーンのカードを直接列挙する。「すべて破壊する」のような
    強制的な全体処理を for_each_stored と組み合わせて表現するために使う。
    """

    def __init__(
        self,
        game,
        player,
        candidates,
        filter_spec,
        store_as,
        source_card=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.candidates = candidates
        self.filter_spec = filter_spec or {}
        self.store_as = store_as
        self.source_card = source_card

    def resolve(self):
        cards = self._candidate_cards()

        evaluator = CardFilterEvaluator(self.game)
        context = {
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
            "package_context": self.package_context,
        }
        matched = [
            card
            for card in cards
            if evaluator.matches(
                card,
                self.filter_spec,
                context,
            )
        ]

        self.package_context[self.store_as] = matched
        return True

    def _candidate_cards(self):
        query = self.game.query

        if self.candidates in (
            "opponent_creatures",
            "opponent_battle_zone",
            "opponent_battle",
        ):
            opponent = query.get_opponent(self.player)
            return query.get_creatures(controller=opponent)

        if self.candidates in (
            "own_creatures",
            "own_battle_zone",
            "own_battle",
        ):
            return query.get_creatures(controller=self.player)

        if self.candidates == "own_other_creatures":
            return [
                creature
                for creature in query.get_creatures(
                    controller=self.player
                )
                if creature is not self.source_card
            ]

        if self.candidates in (
            "creatures",
            "all_creatures",
        ):
            return query.get_creatures()

        if self.candidates in (
            "opponent_elements",
            "opponent_battle_elements",
        ):
            return self._element_cards(
                query.get_opponent(self.player)
            )

        if self.candidates in (
            "own_elements",
            "own_battle_elements",
        ):
            return self._element_cards(self.player)

        if self.candidates in (
            "elements",
            "all_elements",
        ):
            return self._element_cards(None)

        raise ValueError(
            f"Unknown gather_matching candidates: {self.candidates}"
        )

    def _element_cards(self, controller):
        # バトルゾーンの「エレメント」（クリーチャー／フィールド／タマシード等の
        # 場のパーマネント）を集める。進化元（下のカード）は単体のエレメントでは
        # ないため除外する。
        return [
            card
            for card in self.game.query.get_battle_cards(
                controller=controller
            )
            if getattr(card, "is_element", False)
            and not getattr(card, "is_evolution_source", False)
        ]
