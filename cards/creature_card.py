"""
クリーチャーカードを定義するクラス。パワー、種族、タップ状態、召喚酔い、ブロッカー有無などの属性を管理します。
"""

# cards/creature_card.py

from cards.card import (
    Card,
    CardType,
    SpecialType,
)

from actions.summon_action import (
    SummonAction
)

from abilities.keywords.breaker_ability import (
    WBreakerAbility
)

from actions.summon_action import (
    SummonAction
)

from actions.attack_action import (
    AttackAction
)

from core.protocols import PlayableContext
from core.seal_utils import is_seal_card
from ui.debug_log import debug_print
from zones.zone_type import ZoneType


class CreatureCard(Card):

    def __init__(
        self,
        name,
        cost,
        civilizations,
        power,
        hyper_power=None,
        special_types=None,
        name_ja=None,
        effect_name_ja=None,
        race_ja=None,
        effect_texts_ja=None,
    ):

        super().__init__(
            name=name,
            cost=cost,
            civilizations=(
                civilizations
            ),
            card_types=(
                CardType.CREATURE,
            ),
            special_types=special_types,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )

        self.base_power = power
        self.hyper_power = hyper_power

        self.power_modifiers = []

        self.race_ja = (
            race_ja
            if race_ja is not None
            else ()
        )
        self.race = self.race_ja

        # 出たターンを追跡（マッハファイター判定用）
        self.summon_turn = None

        self.evolution_sources = []

        self._inherited_source_modifiers = {}

    @property
    def is_evolution(self):

        if self.has_special_type(
            SpecialType.NEO
        ):
            return (
                self.zone == ZoneType.BATTLE
                and not self.is_evolution_source
                and bool(
                    self.evolution_sources
                )
            )

        return self.has_special_type(
            SpecialType.EVOLUTION
        )

    @property
    def is_neo(self):

        return self.has_special_type(
            SpecialType.NEO
        )

    def add_evolution_source(
        self,
        source,
    ):

        was_evolution_source = getattr(
            source,
            "is_evolution_source",
            False,
        )
        self.evolution_sources.append(source)
        source.is_evolution_source = True
        if was_evolution_source:
            pass
        elif hasattr(
            source,
            "prepare_as_evolution_source",
        ):
            source.prepare_as_evolution_source()
        elif hasattr(
            source,
            "clear_selected_face",
        ):
            source.clear_selected_face()
        self._inherit_source_modifiers(source)
        self._inherit_source_enchant_effects(source)

    def clear_evolution_sources(
        self,
    ):

        sources = list(
            self.evolution_sources
        )
        for source in sources:
            self.release_evolution_source(
                source,
                reactivate=False,
            )

        self.evolution_sources.clear()
        return sources

    def release_evolution_source(
        self,
        source,
        reactivate=True,
    ):

        modifiers = (
            self._inherited_source_modifiers
            .pop(
                source,
                [],
            )
        )

        for modifier in modifiers:
            if modifier in self.power_modifiers:
                self.power_modifiers.remove(
                    modifier
                )
            source.power_modifiers.append(
                modifier
            )

        if source in self.evolution_sources:
            self.evolution_sources.remove(
                source
            )

        self._release_source_enchant_effects(source)

        if reactivate:
            source.is_evolution_source = False

        return source

    def _inherit_source_modifiers(
        self,
        source,
    ):

        modifiers = list(
            getattr(
                source,
                "power_modifiers",
                [],
            )
        )

        if not modifiers:
            self._inherited_source_modifiers[
                source
            ] = []
            return

        for modifier in modifiers:
            source.power_modifiers.remove(
                modifier
            )
            self.power_modifiers.append(
                modifier
            )

        self._inherited_source_modifiers[
            source
        ] = modifiers

    def _inherit_source_enchant_effects(
        self,
        source,
    ):
        for effect in self._enchant_effects_for(
            source,
        ):
            transfer_to = getattr(
                effect,
                "transfer_to",
                None,
            )
            if transfer_to is not None:
                transfer_to(self)

    def _release_source_enchant_effects(
        self,
        source,
    ):
        for effect in self._enchant_effects_for(
            self,
        ):
            if getattr(
                effect,
                "granted_card",
                None,
            ) is not source:
                continue

            transfer_to = getattr(
                effect,
                "transfer_to",
                None,
            )
            if transfer_to is not None:
                transfer_to(source)

    def _enchant_effects_for(
        self,
        card,
    ):
        effects = []
        for attr, values in vars(card).items():
            if not attr.startswith("temporary_"):
                continue

            if not isinstance(
                values,
                list,
            ):
                continue

            effects.extend(
                effect
                for effect in values[:]
                if hasattr(
                    effect,
                    "transfer_to",
                )
            )

        return effects

    def can_exist_in_battle_alone(
        self,
    ):

        return True
    
    def get_break_options(self):

        options = []

        for ability in self.abilities:

            if hasattr(
                ability,
                "get_break_options",
            ):

                options.extend(

                    ability.get_break_options(
                        self
                    )

                )

        # breaker能力なし
        if not options:

            options.append(1)

        debug_print(
            f"{self.name} break options: {options}")

        return options

    def get_current_power(self):

        if is_seal_card(self):
            return 0

        power = self.get_base_power_for_current_mode()

        # Phase 1: additions (positive additive modifiers)
        for modifier in self.power_modifiers:
            if modifier.expired:
                continue
            if getattr(modifier, "kind", "add") == "add" and modifier.amount > 0:
                power += modifier.amount

        # Phase 2: subtractions (negative additive modifiers)
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
                power = (
                    ability.modify_power(
                        self,
                        power,
                    )
                )

        return power

    def get_base_power_for_current_mode(
        self,
    ):

        if (
            self.is_hyper_mode_active
            and self.hyper_power is not None
        ):
            return self.hyper_power

        return self.base_power

    def use(
        self,
        game: PlayableContext,
        player,
        ignore_cost=False,
    ):

        action = SummonAction(
            player,
            self,
            ignore_cost,
        )

        game.action_processor.process(action)

    def play_without_cost(
        self,
        game: PlayableContext,
        player,
    ):

        action = SummonAction(
            player,
            self,
            ignore_cost=True,
        )

        game.action_processor.process(action)

    def reset_battle_state(
        self,
    ):

        self.tapped = False

        self.summoning_sick = False

        self.power_modifiers.clear()

        if hasattr(
            self,
            "temporary_combat_restrictions",
        ):
            self._clear_temporary_effects(
                "temporary_combat_restrictions"
            )

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

        self.lock_hyper_mode()

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
