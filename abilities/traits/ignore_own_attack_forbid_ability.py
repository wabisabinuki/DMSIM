"""自身が持つ「攻撃できない」能力を無視する常在型能力（マーカー）。

スーパーガードマン（`dm26-rp2.R.27/77`）が「ガードマン」を持つクリーチャーへ
付与する。`AttackValidator` は各クリーチャーの `forbids_attack` /
`forbids_attack_player` を走査するが、この能力を持つ攻撃クリーチャーについては、
発生源が攻撃クリーチャー自身（own）である攻撃禁止能力をスキップする。

無視するのは「それら（クリーチャー自身）が持つ攻撃できない能力」だけであり、
他のカード由来の攻撃制限や、効果で付与された一時的な攻撃制限
（`temporary_combat_restrictions`）などの外部由来の制限は無視しない。
"""

from abilities.base.continuous_ability import (
    ContinuousAbility
)


class IgnoreOwnAttackForbidAbility(
    ContinuousAbility
):

    pass
