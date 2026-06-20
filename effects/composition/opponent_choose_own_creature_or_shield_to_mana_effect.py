"""相手が自身のクリーチャーまたはシールドを選んでマナゾーンに置く効果。"""

from effects.base.base_effect import BaseEffect
from zones.zone_type import ZoneType


class OpponentChooseOwnCreatureOrShieldToManaEffect(BaseEffect):
    """鬼丸「V」系の「相手は自身のクリーチャーまたはシールドを1つ選ぶ」。"""

    def __init__(
        self,
        game,
        player,
        optional=False,
        tapped=False,
        prompt=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.optional = optional
        self.tapped = tapped
        self.prompt = prompt or "マナゾーンに置く自身のカードを選ぶ"

    def resolve(self):
        opponent = self.game.query.get_opponent(self.player)
        options = self._options(opponent)
        if not options:
            return False

        target = self.game.target_selector.select(
            opponent,
            options,
            prompt=self.prompt,
            can_skip=self.optional,
        )
        if target is None:
            return False

        from_zone = getattr(target, "zone", None)
        if from_zone not in (ZoneType.BATTLE, ZoneType.SHIELD):
            return False

        moved = self.game.card_mover.move(
            card=target,
            owner=opponent,
            from_zone=from_zone,
            to_zone=ZoneType.MANA,
            reason="opponent_choose_own_creature_or_shield_to_mana",
        )
        if moved and self.tapped is not None:
            target.tapped = bool(self.tapped)

        return moved

    def _options(self, opponent):
        creatures = self.game.query.get_selectable_creatures(
            source=self.source_card or self.player,
            controller=opponent,
        )
        visible_shields = getattr(
            opponent.shield_zone,
            "visible_shields",
            None,
        )
        shields = (
            visible_shields()
            if visible_shields is not None
            else list(opponent.shield_zone.cards)
        )
        return list(creatures) + list(shields)
