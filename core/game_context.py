"""
ゲームの各サブシステム（領域、ルール、アクション等）が相互参照するための共有サービスコンテキスト。
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.game_state import GameState
    from core.card_mover import CardMover
    from core.replacement_manager import ReplacementManager
    from core.event_manager import EventManager
    from core.game_loop import GameLoop
    from core.effect_resolver import EffectResolver
    from core.trigger_manager import TriggerManager
    from core.state_based_actions import StateBasedActions
    from core.action_generator import ActionGenerator
    from core.action_validator import ActionValidator
    from core.action_processor import ActionProcessor
    from core.combat_manager import CombatManager
    from core.validator.attack_validator import AttackValidator
    from core.game_query import GameQuery
    from core.target_selector import TargetSelector
    from core.shield_trigger_resolver import (
        ShieldTriggerResolver,
    )
    from core.setup_manager import SetupManager
    from core.turn_manager import TurnManager
    from core.duration_effect_manager import DurationEffectManager
    from core.seal_manager import SealManager


@dataclass
class ZoneServices:

    card_mover: "CardMover"
    replacement_manager: "ReplacementManager"
    event_manager: "EventManager"


@dataclass
class RuleServices:

    game_loop: "GameLoop"
    effect_resolver: "EffectResolver"
    trigger_manager: "TriggerManager"
    state_based_actions: "StateBasedActions"


@dataclass
class ActionServices:

    action_generator: "ActionGenerator"
    action_validator: "ActionValidator"
    action_processor: "ActionProcessor"
    combat_manager: "CombatManager"
    attack_validator: "AttackValidator"


@dataclass
class GameContext:

    state: "GameState"
    choices: object

    zones: ZoneServices = field(
        repr=False,
        default=None,
    )
    rules: RuleServices = field(
        repr=False,
        default=None,
    )
    actions: ActionServices = field(
        repr=False,
        default=None,
    )

    query: "GameQuery" = field(
        repr=False,
        default=None,
    )
    targets: "TargetSelector" = field(
        repr=False,
        default=None,
    )
    shield_triggers: "ShieldTriggerResolver" = field(
        repr=False,
        default=None,
    )
    setup_manager: "SetupManager" = field(
        repr=False,
        default=None,
    )
    turn_manager: "TurnManager" = field(
        repr=False,
        default=None,
    )
    duration_effect_manager: "DurationEffectManager" = field(
        repr=False,
        default=None,
    )
    seal_manager: "SealManager" = field(
        repr=False,
        default=None,
    )

    resolving: bool = False
    resolving_shield_trigger: bool = False
    _controller: Optional[object] = field(
        repr=False,
        default=None,
    )

    def bind_controller(
        self,
        controller,
    ):

        self._controller = controller

    @property
    def controller(self):

        return self._controller

    @property
    def choice_manager(self):

        return self.choices

    @property
    def card_mover(self):

        return self.zones.card_mover

    @property
    def replacement_manager(self):

        return self.zones.replacement_manager

    @property
    def event_manager(self):

        return self.zones.event_manager

    @property
    def game_loop(self):

        return self.rules.game_loop

    @property
    def effect_resolver(self):

        return self.rules.effect_resolver

    @property
    def trigger_manager(self):

        return self.rules.trigger_manager

    @property
    def state_based_actions(self):

        return self.rules.state_based_actions

    @property
    def action_generator(self):

        return self.actions.action_generator

    @property
    def action_validator(self):

        return self.actions.action_validator

    @property
    def action_processor(self):

        return self.actions.action_processor

    @property
    def combat_manager(self):

        return self.actions.combat_manager

    @property
    def attack_validator(self):

        return self.actions.attack_validator

    @property
    def target_selector(self):

        return self.targets

    @property
    def shield_trigger_resolver(self):

        return self.shield_triggers

    @property
    def duration_effect_manager(self):

        return self._duration_effect_manager

    @duration_effect_manager.setter
    def duration_effect_manager(self, value):

        self._duration_effect_manager = value

    @property
    def seal_manager(self):

        return self._seal_manager

    @seal_manager.setter
    def seal_manager(self, value):

        self._seal_manager = value
