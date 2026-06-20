"""バトルゾーン／シールドゾーンなど、召喚するカード自身以外のパーマネントが
提供する「召喚コスト修飾子」を集約するヘルパー。

`Card.get_current_cost` は、自分の能力による `modify_cost` に加えて、ここで
プレイヤーが支配するパーマネント上の `modify_summon_cost` を持つ能力を走査し、
召喚コストへ反映する。G城（例: グリーン・グランドクロス）のように「自分の
クリーチャーの召喚コストを少なくする」継続効果はこの仕組みで実現する。
"""


def _cost_modifier_abilities(player):
    """player が支配するゾーンから modify_summon_cost を持つ能力を列挙する。"""

    for zone in (
        getattr(player, "shield_zone", None),
        getattr(player, "battle_zone", None),
    ):
        if zone is None:
            continue
        for card in list(zone.cards):
            for ability in getattr(card, "abilities", []):
                modify = getattr(
                    ability,
                    "modify_summon_cost",
                    None,
                )
                if modify is not None:
                    yield modify


def apply_global_summon_cost_modifiers(
    card,
    player,
    cost,
    game,
    consume=False,
    interactive=False,
):
    """召喚コスト ``cost`` に、player の他パーマネント由来の軽減を適用して返す。

    ``consume=True`` のときだけ、「各ターンに1度」等の使用回数を実際に消費する。
    コスト計算（候補列挙・支払い可否判定）では ``consume=False`` で呼び、
    実際に召喚が確定した時点で一度だけ ``consume=True`` で呼ぶこと。

    ``interactive=True`` のときは、「してもよい」軽減についてプレイヤーへ
    使用可否を尋ねる。実際の召喚処理でのみ True にすること（コスト計算や
    支払い可否判定で True にすると同じ選択を何度も尋ねてしまう）。
    """

    if player is None or game is None:
        return cost

    for modify in _cost_modifier_abilities(player):
        cost = modify(
            card,
            player,
            cost,
            game,
            consume=consume,
            interactive=interactive,
        )

    return cost
