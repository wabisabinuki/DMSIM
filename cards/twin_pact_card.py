"""
TwinPactCard: ツインパクトカード（1枚に2つのカード情報を持つカード）。
- 1枚のカードだが、クリーチャーとしても呪文としても使える
- クリーチャー面にCreatureCard、呪文面にSpellCardを持つ設計
"""

from typing import Optional, Union
from cards.card import Card, CardType, Civilization
from cards.creature_card import CreatureCard
from cards.spell_card import SpellCard
from core.seal_utils import is_seal_card
from core.protocols import PlayableContext
from ui.debug_log import debug_print
from actions.summon_action import SummonAction
from actions.cast_spell_action import CastSpellAction


class TwinPactCard(Card):
    """
    ツインパクトカード: 2つの面を持つカード。
    
    特性：
    1. 1枚のカードながらクリーチャーと呪文の両方の情報を持つ
    2. 各面は独立したCreatureCard/SpellCardインスタンス
    3. 使用時に「どちらの面として使用するか」を選択
    4. カード全体の文明は両方の面を結合したもの
    """

    def __init__(
        self,
        name: str,
        creature_face: CreatureCard,
        spell_face: SpellCard,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):
        """
        ツインパクトカードを生成。
        
        Args:
            name: カードの名前
            creature_face: クリーチャー側のCreatureCard
            spell_face: スペル側のSpellCard
        """
        # カード全体の文明は両方の文明を結合
        combined_civilizations = (
            creature_face.civilizations | spell_face.civilizations
        )

        # 基底クラス初期化
        # ツインパクトは両方のタイプを持つ
        super().__init__(
            name=name,
            cost=0,  # ツインパクトは「どちらの面を使うか」で決まるので、ここでは0
            civilizations=combined_civilizations,
            card_types=(CardType.CREATURE, CardType.SPELL),
            name_ja=name_ja,
            effect_name_ja=(
                effect_name_ja
                if effect_name_ja is not None
                else getattr(
                    creature_face,
                    "effect_name_ja",
                    None,
                )
            ),
            effect_texts_ja=(
                effect_texts_ja
                if effect_texts_ja is not None
                else getattr(
                    creature_face,
                    "effect_texts_ja",
                    (),
                )
            ),
        )

        self.creature_face = creature_face
        self.spell_face = spell_face
        self.is_twinpact = True
        self.selected_face: Optional[Union[CreatureCard, SpellCard]] = None

        # クリーチャーとしての属性（クリーチャー面使用時に使用）
        self.base_power = creature_face.base_power if creature_face else 0
        self.power_modifiers = []
        self.race_ja = (
            creature_face.race_ja
            if creature_face
            else None
        )
        self.race = self.race_ja
        self.summon_turn = None
        self._evolution_source_face = None

        # abilitiesは選択された面から取得するため、初期状態では空
        # 選択時にselected_faceのabilitiesをself.abilitiesに設定する

    def _bind_selected_face_abilities(self):
        """
        選択中の面の能力を、この物理カードの能力として扱う。

        ツインパクトは面ではなくカード本体が領域を移動するため、
        owner_card が内側の face を指したままだとゾーン判定や
        event.card との同一性判定に失敗する。
        """
        if not self.selected_face:
            self.abilities = []
            return

        self.abilities = (
            self.selected_face.abilities
            if self.selected_face.abilities
            else []
        )

        for ability in self.abilities:
            if hasattr(ability, "owner_card"):
                ability.owner_card = self

    def _bind_face_abilities(self, abilities):
        for ability in abilities:
            if hasattr(ability, "owner_card"):
                ability.owner_card = self
        return abilities

    def _get_all_face_abilities(self):
        abilities = []
        for face in self.get_all_faces():
            if face and face.abilities:
                abilities.extend(face.abilities)
        return abilities

    def _select_shield_trigger_face(self):
        for as_creature, face in (
            (True, self.creature_face),
            (False, self.spell_face),
        ):
            if not face:
                continue

            if any(
                ability.__class__.__name__ == "ShieldTriggerAbility"
                for ability in face.abilities
            ):
                if as_creature:
                    self.select_creature_face()
                else:
                    self.select_spell_face()
                return True

        return False

    def get_all_faces(self) -> list:
        """全ての面を取得"""
        return [self.creature_face, self.spell_face]

    def select_creature_face(self):
        """
        クリーチャー面を選択する。
        """
        self.selected_face = self.creature_face
        self._bind_selected_face_abilities()

    def select_spell_face(self):
        """
        呪文面を選択する。
        """
        self.selected_face = self.spell_face
        self._bind_selected_face_abilities()

    def clear_selected_face(self):
        """
        面選択をニュートラルに戻す。
        """
        self.selected_face = None
        self._bind_selected_face_abilities()

    def prepare_as_evolution_source(self):
        """
        進化元として下に置く前に、現在の面を記録して中立化する。
        """
        self._evolution_source_face = (
            self.selected_face
        )
        self.clear_selected_face()

    def restore_promoted_face(self):
        """
        進化元から表のバトルゾーンカードに戻った時の面を復元する。
        """
        if (
            self._evolution_source_face
            is self.creature_face
        ):
            self.select_creature_face()
        elif self.creature_face is not None:
            self.select_creature_face()

        self._evolution_source_face = None

    @property
    def cost(self):
        """
        コストプロパティをオーバーライド。
        選択された面のコストを返す。
        """
        if self.selected_face:
            return self.selected_face.cost
        # 選択されていない場合は0（基底クラスの初期値）
        return 0

    @cost.setter
    def cost(self, value):
        """
        コストプロパティのsetter。
        基底クラスの初期化のために必要だが、実際にはselected_faceのコストを使用する。
        """
        # 何もしない（selected_faceのコストを使用するため）
        pass

    def get_current_cost(
        self,
        context: Optional[PlayableContext] = None,
    ) -> int:
        """
        現在のコストを取得。
        
        - selected_faceがある場合: その面のコスト
        - ない場合: エラー
        """
        if is_seal_card(self):
            return 0

        if self.selected_face:
            return self.selected_face.cost
        raise ValueError(
            f"{self.name}: Face not selected. "
            "Use select_creature_face() or select_spell_face() before calling get_current_cost()"
        )

    def get_all_civilizations(self) -> int:
        """
        カード全体の文明を取得（両方の面の文明の結合）。
        マナゾーン内では両方の文明として扱われる。
        """
        if is_seal_card(self):
            return 0

        return (
            self.creature_face.civilizations |
            self.spell_face.civilizations
        )

    def has_creature_type(self) -> bool:
        """ツインパクトはクリーチャータイプを持つ"""
        return True

    def has_spell_type(self) -> bool:
        """ツインパクトは呪文タイプを持つ"""
        return True

    def get_power(self, context: Optional[PlayableContext] = None) -> int:
        """
        パワーを取得。
        クリーチャー面で使用している場合のみ有効。
        """
        if not self.selected_face:
            raise ValueError(
                f"{self.name}: Face not selected"
            )
        if not isinstance(self.selected_face, CreatureCard):
            raise ValueError(
                f"{self.name}: "
                "Cannot get power from spell face"
            )
        return self.get_current_power()

    def get_current_power(self):
        if is_seal_card(self):
            return 0

        power = self.base_power

        # Phase 1: additions
        for modifier in self.power_modifiers:
            if modifier.expired:
                continue
            if getattr(modifier, "kind", "add") == "add" and modifier.amount > 0:
                power += modifier.amount

        # Phase 2: subtractions
        for modifier in self.power_modifiers:
            if modifier.expired:
                continue
            if getattr(modifier, "kind", "add") == "add" and modifier.amount < 0:
                power += modifier.amount

        # Phase 3: multiplications
        for modifier in self.power_modifiers:
            if modifier.expired:
                continue
            if getattr(modifier, "kind", "add") == "multiply":
                power = int(power * getattr(modifier, "factor", 1))

        # Phase 4: divisions
        for modifier in self.power_modifiers:
            if modifier.expired:
                continue
            if getattr(modifier, "kind", "add") == "divide":
                factor = getattr(modifier, "factor", 1)
                if factor:
                    power = int(power // factor)

        # ability query
        for ability in self.abilities:
            if hasattr(ability, "modify_power"):
                power = ability.modify_power(self, power)

        return power

    def get_break_options(self):
        """
        シールドブレイクのオプションを取得。
        """
        options = []

        for ability in self.abilities:
            if hasattr(ability, "get_break_options"):
                options.extend(ability.get_break_options(self))

        # breaker能力なし
        if not options:
            options.append(1)

        debug_print(f"{self.name} break options: {options}")
        return options

    def has_ability(
        self,
        ability_type,
    ):

        if self.are_abilities_ignored():
            return False

        if super().has_ability(
            ability_type
        ):
            return True

        if self.selected_face:
            return any(
                isinstance(
                    ability,
                    ability_type,
                )
                for ability in self.selected_face.abilities
            )

        return any(
            isinstance(
                ability,
                ability_type,
            )
            for ability in self._get_all_face_abilities()
        )

    def reset_battle_state(self):
        """
        バトル状態をリセットする。
        """
        self.tapped = False
        self.summoning_sick = False
        self.power_modifiers.clear()
        if hasattr(
            self,
            "temporary_just_diver_effects",
        ):
            self._clear_temporary_effects(
                "temporary_just_diver_effects"
            )
        if hasattr(
            self,
            "temporary_turn_start_freezes",
        ):
            self._clear_temporary_effects(
                "temporary_turn_start_freezes"
            )
        if hasattr(
            self,
            "temporary_untap_locks",
        ):
            self._clear_temporary_effects(
                "temporary_untap_locks"
            )
        if hasattr(
            self,
            "temporary_ninja_strike_return_effects",
        ):
            self._clear_temporary_effects(
                "temporary_ninja_strike_return_effects"
            )
        self.clear_selected_face()

    def _clear_temporary_effects(
        self,
        attr,
    ):
        values = getattr(
            self,
            attr,
            [],
        )
        for value in values[:]:
            unapply = getattr(
                value,
                "unapply",
                None,
            )
            if unapply is not None:
                unapply()

        values.clear()

    def can_be_cast_as_creature(self) -> bool:
        """
        クリーチャー面として詠唱可能か。
        """
        return self.creature_face is not None

    def can_exist_in_battle_alone(
        self,
    ):

        return self.creature_face is not None

    def can_be_cast_as_spell(self) -> bool:
        """
        呪文面として詠唱可能か。
        """
        return self.spell_face is not None

    def use(
        self,
        game: PlayableContext,
        player,
        ignore_cost=False,
        as_creature: Optional[bool] = None,
    ):
        """
        カードを使用する。
        as_creatureで使用する面を指定する（True=クリーチャー, False=呪文）。
        省略した場合、既にselect_creature_face()またはselect_spell_face()で設定されている面を使用する。
        """
        # 面を選択
        if as_creature is not None:
            if as_creature:
                self.select_creature_face()
            else:
                self.select_spell_face()
        elif not self.selected_face:
            raise ValueError(
                f"{self.name}: Must specify as_creature "
                "(True for creature, False for spell) for TwinPactCard.use(), "
                "or call select_creature_face() or select_spell_face() first"
            )

        # 選択された面に応じて適切なアクションを作成
        if isinstance(self.selected_face, CreatureCard):
            action = SummonAction(
                player,
                self,
                ignore_cost,
            )
        elif isinstance(self.selected_face, SpellCard):
            action = CastSpellAction(
                player,
                self,
                ignore_cost,
            )
        else:
            raise ValueError(f"Unknown selected_face type: {type(self.selected_face)}")

        game.action_processor.process(action)

    def play_without_cost(
        self,
        game: PlayableContext,
        player,
        as_creature: Optional[bool] = None,
    ):
        """
        コストなしでカードを使用する。
        as_creatureで使用する面を指定する（True=クリーチャー, False=呪文）。
        省略した場合、既にselect_creature_face()またはselect_spell_face()で設定されている面を使用する。
        """
        # 面を選択
        if as_creature is not None:
            if as_creature:
                self.select_creature_face()
            else:
                self.select_spell_face()
        elif not self.selected_face:
            if not self._select_shield_trigger_face():
                raise ValueError(
                    f"{self.name}: Must specify as_creature "
                    "(True for creature, False for spell) for TwinPactCard.play_without_cost(), "
                    "or call select_creature_face() or select_spell_face() first"
                )

        # 選択された面に応じて適切なアクションを作成（コスト無視）
        if isinstance(self.selected_face, CreatureCard):
            action = SummonAction(
                player,
                self,
                ignore_cost=True,
            )
        elif isinstance(self.selected_face, SpellCard):
            action = CastSpellAction(
                player=player,
                spell=self,
                ignore_cost=True,
            )
        else:
            raise ValueError(f"Unknown selected_face type: {type(self.selected_face)}")

        game.action_processor.process(action)

    def create_effects(
        self,
        game,
        player,
    ):
        """
        呪文効果を生成する。
        呪文面で使用している場合のみ有効。
        """
        if not self.selected_face:
            raise ValueError(
                f"{self.name}: Face not selected"
            )
        if not isinstance(self.selected_face, SpellCard):
            raise ValueError(
                f"{self.name}: "
                "Cannot create effects from creature face"
            )

        # 呪文面のcreate_effectsを委譲
        return self.selected_face.create_effects(game, player)

    def get_available_actions(
        self,
        game: PlayableContext,
        player,
    ):
        """
        現在の状況で実行可能なアクションを返す。
        ツインパクトカードは両方の面のアクションを返す。
        """
        actions = []

        if self.zone.name == "HAND":
            # クリーチャー面として使用
            if self.creature_face:
                original_face = self.selected_face
                self.select_creature_face()
                can_summon = player.can_play(self)
                self.selected_face = original_face
                self._bind_selected_face_abilities()

                if can_summon:
                    actions.append(
                        SummonAction(
                            player,
                            self,
                        )
                    )

            # 呪文面として使用
            if self.spell_face:
                original_face = self.selected_face
                self.select_spell_face()
                can_cast = player.can_play(self)
                self.selected_face = original_face
                self._bind_selected_face_abilities()

                if can_cast:
                    actions.append(
                        CastSpellAction(
                            player,
                            self,
                        )
                    )

        return actions

    def register_abilities(
        self,
        event_manager,
    ):
        if is_seal_card(self):
            return

        if self.abilities_registered:
            return

        if self.selected_face:
            self._bind_selected_face_abilities()
            return super().register_abilities(
                event_manager,
            )

        abilities = self._bind_face_abilities(
            self._get_all_face_abilities()
        )

        for ability in abilities:
            ability.register(event_manager)

        self.abilities_registered = True

    def __str__(self):
        face_info = (
            f" (selected: {self.selected_face.name})"
            if self.selected_face
            else " [no face selected]"
        )
        return f"{self.name} (TwinPact){face_info}"
