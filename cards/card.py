"""
カードの基底クラス。名前、コスト、所有者、現在の領域、登録能力などの基本プロパティと能力登録処理を管理します。
"""

from enum import Enum, auto

from core.protocols import PlayableContext
from core.seal_utils import is_ignored_by_seal, is_seal_card


class Civilization:
    FIRE = 1 << 0
    WATER = 1 << 1
    NATURE = 1 << 2
    LIGHT = 1 << 3
    DARKNESS = 1 << 4
    # ゼロ文明（無色）。文明の指定を持たず、召喚には文明を問わないマナのみを使う。
    ZERO = 0


class CardType(Enum):
    CREATURE = auto()
    SPELL = auto()
    CROSS_GEAR = auto()
    CASTLE = auto()
    WEAPON = auto()
    FORTRESS = auto()
    HEARTBEAT = auto()
    FIELD = auto()
    CORE = auto()
    AURA = auto()
    CEREMONY = auto()
    ARTIFACT = auto()
    LAND = auto()
    RULE_PLUS = auto()
    TAMASEED = auto()
    DUELIST = auto()
    CELL = auto()


ELEMENT_CARD_TYPES = frozenset(
    (
        CardType.CREATURE,
        CardType.CROSS_GEAR,
        CardType.WEAPON,
        CardType.FORTRESS,
        CardType.HEARTBEAT,
        CardType.FIELD,
        CardType.AURA,
        CardType.ARTIFACT,
        CardType.TAMASEED,
        CardType.DUELIST,
    )
)


class SpecialType:
    EVOLUTION = "evolution"
    NEO = "neo"
    DREAM = "dream"
    HYPER_MODE = "hyper_mode"


class Card:

    def __init__(
        self,
        name: str,
        cost: int,
        civilizations: int,
        card_types,
        special_types=None,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):

        self.name = name
        self.name_ja = name_ja or name
        self.effect_name_ja = (
            effect_name_ja
            or self.name_ja
        )
        self.effect_texts_ja = tuple(
            effect_texts_ja or ()
        )

        self.cost = cost

        self.civilizations = civilizations

        self.card_types = self._normalize_card_types(
            card_types
        )

        self.special_types = tuple(
            special_types or ()
        )

        self.abilities = []

        self.abilities_registered = False

        self.zone_change_counter = 0

        # 状態
        self.tapped = False

        # 現在zone
        self.zone = None

        # 保留状態
        self.is_pending = False
        self.pending_origin_zone = None
        self.pending_reason = None

        # 召喚酔い
        self.summoning_sick = False

        # owner
        self.owner = None

        self.is_evolution_source = False

        self.shield_face_up = False
        self.deck_face_up = False
        self.shield_slot = None
        self.is_fortified_castle = False

        self.hyper_mode_unlocked = False
        self.hyper_mode_controller = None
        self.hyper_mode_expires_on_turn = None
        # 解放した時点のターン番号。失効は「コントローラーの次のターン開始」で
        # 判定するため、固定オフセットではなくこの登録ターンを基準にする
        # （追加ターンが挿入されても正しく1回目のコントローラーターンで失効する）。
        self.hyper_mode_registered_turn = None

    @property
    def is_hyper_mode_active(
        self,
    ):

        return self.hyper_mode_unlocked

    def can_untap(
        self,
        player=None,
        turn_start=False,
    ):

        for lock in getattr(
            self,
            "temporary_untap_locks",
            [],
        ):
            if lock.prevents_untap():
                return False

        if turn_start:
            for freeze in getattr(
                self,
                "temporary_turn_start_freezes",
                [],
            ):
                if freeze.prevents_turn_start_untap_for(
                    player
                ):
                    return False

        return True

    def untap(
        self,
        player=None,
        turn_start=False,
    ):

        if not self.can_untap(
            player=player,
            turn_start=turn_start,
        ):
            return False

        self.tapped = False
        return True

    def unlock_hyper_mode_until_next_turn_start(
        self,
        controller,
        game_state,
    ):

        if self.hyper_mode_unlocked:
            return False

        self.hyper_mode_unlocked = True
        self.hyper_mode_controller = controller
        self.hyper_mode_registered_turn = game_state.turn
        # hyper_mode_expires_on_turn は「通常の交互進行を仮定した目安」で、表示・
        # 後方互換のために残す。実際の失効判定は expire_hyper_modes_for_turn_start
        # が hyper_mode_registered_turn ＋ コントローラー一致で行うため、追加ターン
        # 挿入時もコントローラーの次のターン開始で正しく失効する。
        current = getattr(
            game_state,
            "current_player",
            None,
        )
        offset = (
            2
            if current is None or current is controller
            else 1
        )
        self.hyper_mode_expires_on_turn = game_state.turn + offset
        return True

    def lock_hyper_mode(
        self,
    ):

        self.hyper_mode_unlocked = False
        self.hyper_mode_controller = None
        self.hyper_mode_expires_on_turn = None
        self.hyper_mode_registered_turn = None

    def __str__(self):

        return (
            f"{self.name}"
            f"(Cost:{self.cost})"
        )

    def get_current_cost(
        self,
        player=None,
        game=None,
        consume=False,
        interactive=False,
    ):
        if is_seal_card(self):
            return 0

        cost = self.cost

        for ability in self.abilities:
            modify_cost = getattr(
                ability,
                "modify_cost",
                None,
            )
            if modify_cost is not None:
                cost = modify_cost(
                    self,
                    player,
                    cost,
                    game=game,
                )

        if game is not None and player is not None:
            from core.cost_modifiers import (
                apply_global_summon_cost_modifiers,
            )

            cost = apply_global_summon_cost_modifiers(
                self,
                player,
                cost,
                game,
                consume=consume,
                interactive=interactive,
            )

        return max(
            1,
            int(cost),
        )

    def register_abilities(
        self,
        event_manager,
    ):

        if is_seal_card(self) or is_ignored_by_seal(self):
            return

        if self.abilities_registered:
            return

        for ability in self.abilities:

            ability.register(
                event_manager
            )

        self.abilities_registered = True

    def unregister_abilities(
        self,
    ):

        if not self.abilities_registered:
            return

        for ability in self.abilities:

            ability.unregister()

        self.abilities_registered = False

    def has_ability(
        self,
        ability_type,
    ):

        # 能力無視を受けている間は、持っている能力（付与された能力も含む）を
        # 参照できない。真の付与は実際にこの abilities へ追加されるため、
        # ここで一括して無視される。
        if (
            self.are_abilities_ignored()
            or is_seal_card(self)
            or is_ignored_by_seal(self)
        ):
            return False

        return any(

            isinstance(
                ability,
                ability_type,
            )

            for ability
            in self.abilities
        )

    def are_abilities_ignored(
        self,
    ):
        """このカードの能力が無視されているか（能力無視）を返す。"""

        if is_seal_card(self) or is_ignored_by_seal(self):
            return True

        for nullification in getattr(
            self,
            "temporary_ability_nullifications",
            [],
        ):
            nullifies = getattr(
                nullification,
                "nullifies_abilities",
                None,
            )
            if nullifies is None:
                if nullification:
                    return True
            elif nullifies():
                return True

        return False

    def has_special_type(
        self,
        special_type,
    ):
        if is_seal_card(self):
            return False

        return special_type in self.special_types

    def has_card_type(
        self,
        card_type,
    ):
        if is_seal_card(self):
            return False

        return card_type in self.card_types

    @property
    def is_element(
        self,
    ):
        if is_seal_card(self):
            return False

        return any(
            card_type in ELEMENT_CARD_TYPES
            for card_type in self.card_types
        )

    def is_multicolored(
        self,
    ):
        if is_seal_card(self):
            return False

        civs = self.civilizations

        return (
            civs & (civs - 1)
        ) != 0

    def can_exist_in_battle_alone(
        self,
    ):

        return False

    def play(
        self,
        game: PlayableContext,
        player,
    ):

        raise NotImplementedError
    
    def use(
        self,
        game: PlayableContext,
        player,
        ignore_cost=False,
    ):

        raise NotImplementedError()

    def play_without_cost(
        self,
        game: PlayableContext,
        player,
    ):

        raise NotImplementedError

    def get_available_actions(
        self,
        game: PlayableContext,
        player,
    ):

        return []

    def _normalize_card_types(
        self,
        card_types,
    ):

        if isinstance(card_types, CardType):
            return (card_types,)

        return tuple(card_types)
