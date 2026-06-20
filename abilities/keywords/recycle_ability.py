"""Recycle keyword ability.

リサイクル：この呪文を自分の墓地からリサイクルコストを支払って唱えてもよい。
こうして唱えた後、墓地のかわりに山札の下に置く。

墓地にあるこの呪文が自分のメインステップ中にアクションとして提供される。
唱えた場合、カードは墓地ではなく山札の下へ移動する。
コストは通常の詠唱コストとは別に指定される。
"""

from abilities.base.base_ability import BaseAbility
from actions.cast_spell_action import CastSpellAction
from cards.card import Civilization
from core.game_step import GameStep
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


_CIVILIZATION_MAP = {
    "fire": Civilization.FIRE,
    "water": Civilization.WATER,
    "nature": Civilization.NATURE,
    "light": Civilization.LIGHT,
    "darkness": Civilization.DARKNESS,
}


def _parse_civilizations(names):
    # 文字列単体・文字列リストのどちらも受け付ける
    if isinstance(names, str):
        names = [names]
    value = 0
    for name in names:
        key = name.lower()
        if key not in _CIVILIZATION_MAP:
            raise ValueError(f"recycle: Unknown civilization: {name}")
        value |= _CIVILIZATION_MAP[key]
    return value


class RecycleAbility(BaseAbility):

    cast_destination = ZoneType.DECK  # 唱えた後に山札の下へ

    def __init__(
        self,
        owner_card,
        game,
        recycle_cost,
        recycle_civilizations=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.recycle_cost = int(recycle_cost)
        # None = カード本来の文明を使用
        self.recycle_civilizations = recycle_civilizations

    def _effective_civilizations(self):
        if self.recycle_civilizations is not None:
            return self.recycle_civilizations
        return getattr(self.owner_card, "civilizations", 0)

    def get_play_actions(
        self,
        player,
        source_card,
    ):
        if source_card is not self.owner_card:
            return []
        if not self._can_offer_to(player):
            return []

        action = CastSpellAction(
            player,
            self.owner_card,
            play_permission=self,
        )
        action.cost_override = self.recycle_cost
        action.cost_override_civilizations = self._effective_civilizations()
        return [action]

    def can_use_for(
        self,
        player,
        card,
    ):
        return (
            card is self.owner_card
            and self._can_offer_to(player)
        )

    def _can_offer_to(
        self,
        player,
    ):
        state = self.game.state
        if state.step != GameStep.MAIN:
            return False
        if state.current_player is not player:
            return False
        if getattr(self.owner_card, "owner", None) is not player:
            return False
        if getattr(self.owner_card, "zone", None) != ZoneType.GRAVEYARD:
            return False
        if is_card_pending(self.owner_card):
            return False
        if self.owner_card not in player.graveyard.cards:
            return False
        return player.can_pay_cost(self.recycle_cost, self._effective_civilizations())

    def __str__(
        self,
    ):
        return f"Recycle: {self.owner_card.name}"


def build_recycle_ability(
    spec,
    card,
    game,
):
    cost = spec.get(
        "recycle_cost",
        spec.get("cost"),
    )
    if cost is None:
        raise ValueError("recycle requires recycle_cost")

    # recycle_civilizations（リスト）/ civilization（文字列 or リスト）の両対応。
    # 省略時はカード本来の文明を使用する。
    raw_civs = spec.get(
        "recycle_civilizations",
        spec.get(
            "civilizations",
            spec.get("civilization"),
        ),
    )
    recycle_civilizations = (
        _parse_civilizations(raw_civs) if raw_civs is not None else None
    )

    return RecycleAbility(
        owner_card=card,
        game=game,
        recycle_cost=cost,
        recycle_civilizations=recycle_civilizations,
    )
