"""
シミュレータの最上位管理クラス。各サブシステムを接続・初期化し、ゲームの開始や全体制御を行います。
"""

# core/game_controller.py

from typing import Optional

from core.game_state import GameState
from core.game_context import (
    GameContext,
    ZoneServices,
    RuleServices,
    ActionServices,
)
from core.card_mover import CardMover
from core.action_generator import ActionGenerator
from core.action_validator import ActionValidator
from core.action_processor import ActionProcessor
from core.effect_resolver import EffectResolver
from core.game_loop import GameLoop
from core.trigger_manager import TriggerManager
from core.replacement_manager import ReplacementManager
from core.state_based_actions import StateBasedActions
from core.event_manager import EventManager
from core.combat_manager import CombatManager
from core.setup_manager import SetupManager
from core.game_query import GameQuery
from core.target_selector import TargetSelector
from core.shield_trigger_resolver import (
    ShieldTriggerResolver,
)
from core.turn_manager import TurnManager
from core.validator.attack_validator import (
    AttackValidator,
)
from core.duration_effect_manager import DurationEffectManager
from core.seal_manager import SealManager
from core.turn_stats_manager import TurnStatsManager
from ui.game_presenter import (
    GamePresenter,
    NullGamePresenter,
)


class GameController:

    def __init__(
        self,
        players,
        choice_manager,
        presenter: Optional[GamePresenter] = None,
        enforce_victory_conditions=True,
    ):

        if presenter is None:
            presenter = NullGamePresenter()

        self.presenter = presenter

        self.context = GameContext(
            state=GameState(
                players,
                enforce_victory_conditions=(
                    enforce_victory_conditions
                ),
            ),
            choices=choice_manager,
        )

        self._wire_subsystems()

        self.context.bind_controller(self)
        bind_choice_manager = getattr(
            choice_manager,
            "bind_context",
            None,
        )
        if bind_choice_manager is not None:
            bind_choice_manager(self.context)

        bind_presenter = getattr(
            self.presenter,
            "bind_context",
            None,
        )
        if bind_presenter is not None:
            bind_presenter(self.context)

    def _wire_subsystems(self):

        ctx = self.context

        event_manager = EventManager()

        ctx.zones = ZoneServices(
            event_manager=event_manager,
            replacement_manager=(
                ReplacementManager(ctx)
            ),
            card_mover=CardMover(ctx),
        )

        ctx.rules = RuleServices(
            effect_resolver=EffectResolver(),
            trigger_manager=TriggerManager(ctx),
            state_based_actions=(
                StateBasedActions(ctx)
            ),
            game_loop=GameLoop(ctx),
        )

        attack_validator = AttackValidator(ctx)
        action_validator = ActionValidator(ctx)

        ctx.actions = ActionServices(
            attack_validator=attack_validator,
            action_validator=action_validator,
            action_generator=ActionGenerator(
                ctx,
                action_validator,
            ),
            action_processor=ActionProcessor(
                self,
                action_validator,
            ),
            combat_manager=CombatManager(ctx),
        )

        ctx.targets = TargetSelector(ctx)
        ctx.query = GameQuery(ctx)
        ctx.shield_triggers = ShieldTriggerResolver(
            ctx,
        )
        ctx.setup_manager = SetupManager(ctx)
        ctx.turn_manager = TurnManager(
            ctx,
            self.presenter,
        )
        ctx.duration_effect_manager = DurationEffectManager(
            ctx,
        )
        ctx.seal_manager = SealManager(ctx)
        ctx.turn_stats_manager = TurnStatsManager(ctx)

    def start_game(self):

        self.context.setup_manager.setup_game()

    @property
    def state(self):

        return self.context.state

    @property
    def choice_manager(self):

        return self.context.choices

    @property
    def resolving(self):

        return self.context.resolving

    @resolving.setter
    def resolving(self, value):

        self.context.resolving = value

    @property
    def card_mover(self):

        return self.context.zones.card_mover

    @property
    def replacement_manager(self):

        return self.context.zones.replacement_manager

    @property
    def event_manager(self):

        return self.context.zones.event_manager

    @property
    def game_loop(self):

        return self.context.rules.game_loop

    @property
    def effect_resolver(self):

        return self.context.rules.effect_resolver

    @property
    def trigger_manager(self):

        return self.context.rules.trigger_manager

    @property
    def state_based_actions(self):

        return self.context.rules.state_based_actions

    @property
    def action_generator(self):

        return self.context.actions.action_generator

    @property
    def action_validator(self):

        return self.context.actions.action_validator

    @property
    def action_processor(self):

        return self.context.actions.action_processor

    @property
    def combat_manager(self):

        return self.context.actions.combat_manager

    @property
    def attack_validator(self):

        return self.context.actions.attack_validator

    @property
    def target_selector(self):

        return self.context.targets

    @property
    def shield_trigger_resolver(self):

        return self.context.shield_triggers

    @property
    def query(self):

        return self.context.query

    @property
    def setup_manager(self):

        return self.context.setup_manager

    @property
    def turn_manager(self):

        return self.context.turn_manager

    @property
    def duration_effect_manager(self):

        return self.context.duration_effect_manager

    @property
    def seal_manager(self):

        return self.context.seal_manager

    @property
    def turn_stats_manager(self):

        return self.context.turn_stats_manager
