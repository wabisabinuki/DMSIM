"""「（このクリーチャーは）可能なら攻撃する」を表す常在型能力。

スペース・チャージ等で特定のクリーチャーに一時的に付与され、付与されている間、
その持ち主のクリーチャーは可能であれば攻撃しなければならない。``ActionValidator.
_is_attack_required`` が攻撃クリーチャー自身の能力も走査し、``requires_attack`` が
True を返すと攻撃を強制する（攻撃可能な対象がない場合などは強制されない）。

オピオン型の ``OpponentAttackMandatoryAbility``（相手全体を強制）と違い、
**この能力の持ち主自身**だけを対象にする点が異なる。
"""

from abilities.base.continuous_ability import ContinuousAbility


class MustAttackAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        game,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game

    def requires_attack(
        self,
        holder,
        attacker,
    ):
        # 自身が攻撃クリーチャーのときだけ強制する。
        return attacker is self.owner_card


def build_must_attack_ability(
    spec,
    card,
    game,
):
    return MustAttackAbility(
        owner_card=card,
        game=game,
    )
