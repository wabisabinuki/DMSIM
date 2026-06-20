"""
バトルゾーンからクリーチャーを2体選んでバトルさせる効果。
（クリーチャーを2体選ぶ。その2体をバトルさせる。）
同一プレイヤーのクリーチャー同士でもバトル可能。
"""

from actions.attack_creature_action import AttackCreatureAction
from effects.base.base_effect import BaseEffect


class BattleTwoCreaturesEffect(BaseEffect):
    """
    コントローラーが任意のクリーチャー2体を選んでバトルさせる。
    同一コントローラーのクリーチャー同士でもバトルできる。
    """

    def __init__(
        self,
        player,
        game,
        optional=False,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.optional = optional

    def can_attempt(self):
        return len(self.game.query.get_battle_cards()) >= 2

    def resolve(self):
        all_creatures = self.game.query.get_battle_cards()
        if len(all_creatures) < 2:
            return False

        attacker = self.game.target_selector.select(
            self.player,
            all_creatures,
            prompt="バトルさせるクリーチャーを1体選ぶ（攻撃側）",
            can_skip=self.optional,
        )
        if attacker is None:
            return False

        defender_candidates = [c for c in all_creatures if c is not attacker]
        if not defender_candidates:
            return False

        defender = self.game.target_selector.select(
            self.player,
            defender_candidates,
            prompt="バトルさせるクリーチャーを1体選ぶ（防御側）",
            can_skip=self.optional,
        )
        if defender is None:
            return False

        self.game.combat_manager.process_battle(
            AttackCreatureAction(attacker.owner, attacker, defender)
        )
        return True
