"""Grant normal main-step play actions from non-hand zones."""

from abilities.base.base_ability import BaseAbility
from actions.cast_spell_action import CastSpellAction
from actions.summon_action import SummonAction
from cards.creature_card import CreatureCard
from cards.spell_card import SpellCard
from cards.twin_pact_card import TwinPactCard
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


ZONE_TYPES = {
    "battle": ZoneType.BATTLE,
    "battle_zone": ZoneType.BATTLE,
    "grave": ZoneType.GRAVEYARD,
    "graveyard": ZoneType.GRAVEYARD,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "mana_zone": ZoneType.MANA,
    "shield": ZoneType.SHIELD,
    "shield_zone": ZoneType.SHIELD,
}


class PlayFromZoneAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
        zones,
        card_types=None,
        affected_player="controller",
        active_zone=ZoneType.BATTLE,
        per_turn=None,
        follow_up=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.zones = tuple(
            _zone_type(zone)
            for zone in zones
        )
        self.card_types = frozenset(
            _card_type_name(card_type)
            for card_type in _as_list(
                card_types
                or (
                    "creature",
                    "spell",
                )
            )
        )
        self.affected_player = affected_player
        self.active_zone = _zone_type(active_zone)
        self.per_turn = (
            None
            if per_turn is None
            else int(per_turn)
        )
        self.follow_up = follow_up
        # ターン番号 -> このターンに使用した回数
        self._uses_by_turn = {}

    def get_play_actions(
        self,
        player,
        source_card,
    ):
        if source_card is not self.owner_card:
            return []

        if not self._is_active():
            return []

        if not self._affects(player):
            return []

        if not self._per_turn_available():
            return []

        actions = []
        for zone in self.zones:
            for card in player.get_zone(zone).cards:
                if (
                    is_card_pending(card)
                    or getattr(card, "owner", None) is not player
                ):
                    continue

                actions.extend(
                    self._actions_for_card(
                        player,
                        card,
                    )
                )

        return actions

    def _actions_for_card(
        self,
        player,
        card,
    ):
        actions = []
        if (
            "creature" in self.card_types
            and isinstance(card, CreatureCard)
        ):
            actions.append(
                SummonAction(
                    player,
                    card,
                    play_permission=self,
                    play_permissions=[self],
                )
            )

        if (
            "spell" in self.card_types
            and isinstance(card, SpellCard)
        ):
            actions.append(
                CastSpellAction(
                    player,
                    card,
                    play_permission=self,
                    play_permissions=[self],
                )
            )

        if isinstance(card, TwinPactCard):
            if (
                "creature" in self.card_types
                and card.creature_face is not None
            ):
                actions.append(
                SummonAction(
                    player,
                    card,
                    play_permission=self,
                    play_permissions=[self],
                )
            )

            if (
                "spell" in self.card_types
                and card.spell_face is not None
            ):
                actions.append(
                CastSpellAction(
                    player,
                    card,
                    play_permission=self,
                    play_permissions=[self],
                )
            )

        return actions

    def _affects(
        self,
        player,
    ):
        if self.affected_player in (
            "controller",
            "owner",
            "self",
        ):
            return player is self.owner_card.owner

        if self.affected_player == "opponent":
            return player is not self.owner_card.owner

        if self.affected_player == "all":
            return True

        return False

    def can_use_for(
        self,
        player,
        card,
    ):
        if not self._is_active():
            return False

        if not self._affects(player):
            return False

        if not self._per_turn_available():
            return False

        if getattr(
            card,
            "owner",
            None,
        ) is not player:
            return False

        zone = getattr(
            card,
            "zone",
            None,
        )
        if zone not in self.zones:
            return False

        if (
            zone is None
            or card not in player.get_zone(zone).cards
            or is_card_pending(card)
        ):
            return False

        return self._can_play_card_type(card)

    def mark_used(
        self,
        player,
        card,
    ):
        # この許可で実際に召喚が成功した時に呼ばれる（summon handler 経由）。
        # 各ターンの使用回数を消費し、続けて「そうしたら」の後続効果を発動する。
        if self.per_turn is not None:
            turn = self._current_turn()
            if turn is not None:
                self._uses_by_turn[turn] = (
                    self._uses_by_turn.get(turn, 0) + 1
                )

        self._resolve_follow_up(player)

    def _is_active(
        self,
    ):
        if is_card_pending(self.owner_card):
            return False

        if getattr(
            self.owner_card,
            "zone",
            None,
        ) != self.active_zone:
            return False

        # 城（シールドゾーンのパーマネント）は表向きの間だけアクティブ。
        if (
            self.active_zone == ZoneType.SHIELD
            and not getattr(
                self.owner_card,
                "shield_face_up",
                False,
            )
        ):
            return False

        return True

    def _per_turn_available(
        self,
    ):
        if self.per_turn is None:
            return True

        turn = self._current_turn()
        if turn is None:
            return True

        return self._uses_by_turn.get(turn, 0) < self.per_turn

    def _current_turn(
        self,
    ):
        state = getattr(self.game, "state", None)
        return getattr(state, "turn", None)

    def _resolve_follow_up(
        self,
        player,
    ):
        if not self.follow_up:
            return

        # 召喚解決の直後（pending 解除後）にキューへ積み、通常の効果解決
        # ループで処理させる。汎用の move 効果などをそのまま合成できる。
        from effects.effect_factory import EffectFactory
        from effects.composition.packaged_effect import PackagedEffect

        effects = EffectFactory(self.game).build_many(
            self.follow_up,
            player,
            source_card=self.owner_card,
        )
        if not effects:
            return

        package = PackagedEffect(
            effects,
            label=f"{self.owner_card.name} follow-up",
        )
        package.package_context = {}
        package.source_card = self.owner_card
        self.game.effect_resolver.add_effect(
            package,
            controller=player,
        )

    def _can_play_card_type(
        self,
        card,
    ):
        if (
            "creature" in self.card_types
            and isinstance(card, CreatureCard)
        ):
            return True

        if (
            "spell" in self.card_types
            and isinstance(card, SpellCard)
        ):
            return True

        if isinstance(card, TwinPactCard):
            return (
                (
                    "creature" in self.card_types
                    and card.creature_face is not None
                )
                or (
                    "spell" in self.card_types
                    and card.spell_face is not None
                )
            )

        return False

    def __str__(
        self,
    ):
        return (
            f"{self.owner_card.name} play from zone"
        )


def build_play_from_zone_ability(
    spec,
    card,
    game,
):
    zones = spec.get(
        "zones",
        spec.get(
            "from_zones",
            spec.get(
                "from_zone",
                spec.get("zone"),
            ),
        ),
    )
    if zones is None:
        raise ValueError("play_from_zone requires zone or zones")

    if not isinstance(zones, list):
        zones = [zones]

    return PlayFromZoneAbility(
        owner_card=card,
        game=game,
        zones=zones,
        card_types=spec.get(
            "card_types",
            spec.get("card_type"),
        ),
        affected_player=spec.get(
            "affected_player",
            "controller",
        ),
        active_zone=spec.get(
            "active_zone",
            "battle",
        ),
        per_turn=spec.get("per_turn"),
        follow_up=spec.get("follow_up"),
    )


def _zone_type(
    value,
):
    if isinstance(
        value,
        ZoneType,
    ):
        return value

    key = str(value).lower()
    if key not in ZONE_TYPES:
        raise ValueError(f"Unknown play_from_zone zone: {value}")

    return ZONE_TYPES[key]


def _card_type_name(
    value,
):
    return str(value).lower()


def _as_list(
    value,
):
    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]
