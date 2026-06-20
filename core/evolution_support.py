"""進化クリーチャーの進化元の判定・選択・スタックを行う共有ヘルパー。

召喚処理（``summon_action_handler``）と、超次元ゾーンからの遅延登場
（``super_dimension_release_effect``）のように、進化クリーチャーを
バトルゾーンへ出す複数の経路から同じロジックを使う。
"""

from abilities.keywords.evolution_ability import EvolutionAbility
from cards.card import SpecialType
from zones.zone_type import ZoneType


def evolution_ability(card):
    """カードが持つ ``EvolutionAbility`` を返す（無ければ None）。"""

    for ability in getattr(card, "abilities", []):
        if isinstance(ability, EvolutionAbility):
            return ability

    return None


def requires_evolution_source(card):
    """進化元を必須とする進化クリーチャーかどうか（NEO は任意なので除外）。"""

    return (
        card.has_special_type(SpecialType.EVOLUTION)
        and not card.has_special_type(SpecialType.NEO)
        and evolution_ability(card) is not None
    )


def evolution_source_candidates(player, card):
    """指定ゾーン（バトル/墓地/手札/マナ）から進化元候補を集める。"""

    ability = evolution_ability(card)
    if ability is None:
        return []

    return ability.source_candidates(player, card)


def source_count_for(card):
    ability = evolution_ability(card)
    return getattr(ability, "source_count", 1)


def stack_evolution_sources(player, card, sources):
    """選んだ進化元を供給ゾーンから取り出し、進化クリーチャーの下へ重ねる。"""

    if not isinstance(sources, list):
        sources = [sources]

    ability = evolution_ability(card)
    source_zone = (
        ability.source_zone
        if ability is not None
        else ZoneType.BATTLE
    )
    zone = player.get_zone(source_zone)

    for source in sources:
        zone.remove(source)
        card.add_evolution_source(source)
        source.zone = ZoneType.BATTLE
        source.owner = player
