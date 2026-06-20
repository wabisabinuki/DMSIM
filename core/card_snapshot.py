"""
カードの特定時点の情報を扱うスナップショット群。

``CardSnapshot`` は従来どおり同一性確認用、``EffectSource`` は効果の
発生源情報を live / Last Known Information として参照するために使う。
"""

from dataclasses import dataclass
import time
from zones.zone_type import ZoneType


class CardSnapshot:
    """
    Trigger 発動時のカード状態スナップショット
    
    Effect が解決時に「このスナップショット時の条件がまだ有効か」を判定する際に使用。
    
    用途:
    - 「このカードが場にいる間」という継続条件の判定
    - Zone 移動後のカード同一性検証
    - 複数 Effect の相互作用時の順序保証
    """

    def __init__(self, card):
        """
        Args:
            card: Trigger 発動時のカード
        """
        self.zone_change_counter = card.zone_change_counter
        self.zone = card.zone
        self.owner = card.owner
        self.timestamp = time.time()

    def is_same_card(self, card) -> bool:
        """
        カードが同一（Zone 移動で別物になってないか）

        Returns:
            True: カードが同一
            False: カードが別物（Zone 移動後など）
        """
        return (
            self.zone_change_counter == card.zone_change_counter
        )

    def is_still_in_zone(
        self,
        card,
        expected_zone: ZoneType,
    ) -> bool:
        """
        カードが指定 Zone に留まっているか

        Args:
            card: 検証対象のカード
            expected_zone: 期待されるZone

        Returns:
            True: カードが同一かつ指定 Zone にいる
            False: カードが別物か異なる Zone にいる
        """
        if not self.is_same_card(card):
            return False
        
        return card.zone == expected_zone

    def is_still_in_battle(self, card) -> bool:
        """
        カードが場（Battle Zone）に留まっているか

        Args:
            card: 検証対象のカード

        Returns:
            True: カードが同一かつ Battle Zone にいる
            False: カードが別物か Battle Zone 以外にいる
        """
        return self.is_still_in_zone(
            card,
            ZoneType.BATTLE,
        )

    def __str__(self):
        return (
            f"CardSnapshot("
            f"zcc={self.zone_change_counter}, "
            f"zone={self.zone}"
            f")"
        )


@dataclass(frozen=True)
class CardInfoSnapshot:
    """
    効果の発生源情報参照用スナップショット。

    owner / controller は identity 用の参照として保持する。snapshot から
    手札枚数などの mutable な現在状態を読まないこと。
    """

    card_id: object
    instance_id: int
    name: str
    name_ja: str
    effect_name_ja: str
    owner: object
    controller: object
    zone: object
    zone_change_counter: int
    cost: object
    power: int
    civilizations: int
    races: tuple
    races_ja: tuple
    card_types: tuple
    special_types: tuple
    tapped: bool
    shield_face_up: bool
    deck_face_up: bool
    is_evolution: bool
    is_evolution_source: bool
    contained_card_count: int
    contained_cards: tuple
    ability_ids: tuple
    ability_types: tuple
    timestamp: float

    @classmethod
    def capture(
        cls,
        card,
        game=None,
        player=None,
    ):
        contained_cards = tuple(
            _contained_card_snapshots(
                card,
                game=game,
                player=player,
                seen={
                    id(card),
                },
            )
        )
        abilities = tuple(
            getattr(
                card,
                "abilities",
                (),
            )
            or ()
        )
        return cls(
            card_id=getattr(
                card,
                "card_id",
                None,
            ),
            instance_id=id(card),
            name=getattr(
                card,
                "name",
                "",
            ),
            name_ja=getattr(
                card,
                "name_ja",
                getattr(card, "name", ""),
            ),
            effect_name_ja=getattr(
                card,
                "effect_name_ja",
                getattr(card, "name_ja", getattr(card, "name", "")),
            ),
            owner=getattr(
                card,
                "owner",
                None,
            ),
            controller=getattr(
                card,
                "controller",
                getattr(card, "owner", None),
            ),
            zone=getattr(
                card,
                "zone",
                None,
            ),
            zone_change_counter=getattr(
                card,
                "zone_change_counter",
                0,
            ),
            cost=_current_cost(
                card,
                game=game,
                player=player,
            ),
            power=_current_power(card),
            civilizations=getattr(
                card,
                "civilizations",
                0,
            )
            or 0,
            races=tuple(
                _as_tuple(
                    getattr(
                        card,
                        "race",
                        (),
                    )
                )
            ),
            races_ja=tuple(
                _as_tuple(
                    getattr(
                        card,
                        "race_ja",
                        (),
                    )
                )
            ),
            card_types=tuple(
                getattr(
                    card,
                    "card_types",
                    (),
                )
                or ()
            ),
            special_types=tuple(
                getattr(
                    card,
                    "special_types",
                    (),
                )
                or ()
            ),
            tapped=bool(
                getattr(
                    card,
                    "tapped",
                    False,
                )
            ),
            shield_face_up=bool(
                getattr(
                    card,
                    "shield_face_up",
                    False,
                )
            ),
            deck_face_up=bool(
                getattr(
                    card,
                    "deck_face_up",
                    False,
                )
            ),
            is_evolution=bool(
                getattr(
                    card,
                    "is_evolution",
                    False,
                )
            ),
            is_evolution_source=bool(
                getattr(
                    card,
                    "is_evolution_source",
                    False,
                )
            ),
            contained_card_count=1 + len(contained_cards),
            contained_cards=contained_cards,
            ability_ids=tuple(
                _ability_id(ability)
                for ability in abilities
            ),
            ability_types=tuple(
                type(ability).__name__
                for ability in abilities
            ),
            timestamp=time.time(),
        )

    def get_property(
        self,
        name,
    ):
        attr = _PROPERTY_ALIASES.get(
            name,
            name,
        )
        if not hasattr(
            self,
            attr,
        ):
            raise AttributeError(
                f"Unknown card info property: {name}"
            )

        value = getattr(
            self,
            attr,
        )
        if attr == "zone":
            return _zone_name(value)
        if attr == "card_types":
            return tuple(
                _card_type_name(card_type)
                for card_type in value
            )
        return value


class EffectSource:
    """
    効果の発生源情報を live または frozen LKI として参照する。
    """

    def __init__(
        self,
        live_card,
        game=None,
        player=None,
    ):
        self.live_card = live_card
        self.live_zone_change_counter = getattr(
            live_card,
            "zone_change_counter",
            None,
        )
        self.game = game
        self.player = player or getattr(
            live_card,
            "owner",
            None,
        )
        self.frozen_snapshot = None

    def is_live(
        self,
    ) -> bool:
        if self.frozen_snapshot is not None:
            return False

        if self.live_card is None:
            return False

        return (
            getattr(
                self.live_card,
                "zone_change_counter",
                None,
            )
            == self.live_zone_change_counter
        )

    def freeze(
        self,
    ):
        if self.frozen_snapshot is not None:
            return self.frozen_snapshot

        if self.live_card is None:
            return None

        self.frozen_snapshot = CardInfoSnapshot.capture(
            self.live_card,
            game=self.game,
            player=self.player,
        )
        return self.frozen_snapshot

    def snapshot(
        self,
    ):
        if self.is_live():
            return CardInfoSnapshot.capture(
                self.live_card,
                game=self.game,
                player=self.player,
            )

        if self.frozen_snapshot is None:
            self.freeze()

        return self.frozen_snapshot

    def get_current_or_snapshot(
        self,
    ):
        return self.snapshot()

    def get_property(
        self,
        name,
    ):
        snapshot = self.snapshot()
        if snapshot is None:
            return None

        return snapshot.get_property(name)

    def is_source_card(
        self,
        card,
    ) -> bool:
        return self.live_card is card


def effect_uses_source_info(
    value,
) -> bool:
    return _contains_source_info(
        value,
        seen=set(),
    )


def _contains_source_info(
    value,
    seen,
) -> bool:
    if value is None:
        return False

    value_id = id(value)
    if value_id in seen:
        return False
    seen.add(value_id)

    if isinstance(value, str):
        return (
            value == "source_info"
            or value.startswith("source_info.")
        )

    if isinstance(value, dict):
        if value.get("from") == "source_info":
            return True
        ref = value.get("ref")
        if isinstance(ref, str) and (
            ref == "source_info"
            or ref.startswith("source_info.")
        ):
            return True
        return any(
            _contains_source_info(item, seen)
            for item in value.values()
        )

    if isinstance(value, (list, tuple, set)):
        return any(
            _contains_source_info(item, seen)
            for item in value
        )

    if not hasattr(
        value,
        "__dict__",
    ):
        return False

    for key, item in vars(value).items():
        if key in (
            "game",
            "source_card",
            "source_info",
            "trigger_snapshot",
            "condition_context",
            "package_context",
            "player",
            "owner",
            "target",
            "target_card",
        ):
            continue
        if _contains_source_info(item, seen):
            return True

    return False


_PROPERTY_ALIASES = {
    "id": "card_id",
    "object_id": "instance_id",
    "instance": "instance_id",
    "zcc": "zone_change_counter",
    "contained_count": "contained_card_count",
    "contained_card_snapshots": "contained_cards",
    "abilities": "ability_ids",
    "ability_id": "ability_ids",
    "ability_types": "ability_types",
    "types": "card_types",
    "card_type": "card_types",
    "civilization": "civilizations",
    "race": "races",
    "race_ja": "races_ja",
}


def _contained_card_snapshots(
    card,
    game=None,
    player=None,
    seen=None,
):
    seen = seen or set()
    result = []
    for child in _contained_children(card):
        child_id = id(child)
        if child_id in seen:
            continue
        seen.add(child_id)
        result.append(
            CardInfoSnapshot.capture(
                child,
                game=game,
                player=player,
            )
        )
        result.extend(
            _contained_card_snapshots(
                child,
                game=game,
                player=player,
                seen=seen,
            )
        )
    return result


def _contained_children(
    card,
):
    children = []
    for attr in (
        "evolution_sources",
        "linked_cards",
        "component_cards",
    ):
        children.extend(
            getattr(
                card,
                attr,
                (),
            )
            or ()
        )
    return children


def _current_cost(
    card,
    game=None,
    player=None,
):
    get_current_cost = getattr(
        card,
        "get_current_cost",
        None,
    )
    if get_current_cost is not None:
        for kwargs in (
            {
                "player": player,
                "game": game,
            },
            {
                "player": player,
            },
            {
                "game": game,
            },
            {},
        ):
            try:
                return get_current_cost(**kwargs)
            except TypeError:
                continue
            except ValueError:
                break

    return getattr(
        card,
        "cost",
        None,
    )


def _current_power(
    card,
):
    get_current_power = getattr(
        card,
        "get_current_power",
        None,
    )
    if get_current_power is not None:
        return get_current_power()

    return getattr(
        card,
        "base_power",
        0,
    )


def _ability_id(
    ability,
):
    return (
        getattr(
            ability,
            "ability_id",
            None,
        )
        or type(ability).__name__
    )


def _as_tuple(
    value,
):
    if value is None:
        return ()

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return tuple(value)

    return (value,)


def _zone_name(
    zone,
):
    if zone is None:
        return None

    return getattr(
        zone,
        "name",
        str(zone),
    ).lower()


def _card_type_name(
    card_type,
):
    return getattr(
        card_type,
        "name",
        str(card_type),
    ).lower()
