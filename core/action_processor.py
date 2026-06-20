"""
プレイヤーが発起した各種アクションを受け取り、検証を行った後、適切なアクションハンドラへ処理を振り分けるプロセッサ。
"""

from actions.summon_action import (
    SummonAction
)

from actions.attack_action import (
    AttackAction
)

from actions.proceed_to_attack_step_action import (
    ProceedToAttackStepAction,
)

from actions.finish_attack_step_action import (
    FinishAttackStepAction,
)

from actions.destroy_action import (
    DestroyAction
)

from actions.destroy_multiple_action import (
    DestroyMultipleAction
)

from actions.attack_creature_action import (
    AttackCreatureAction
)

from actions.cast_spell_action import (
    CastSpellAction
)

from actions.use_card_action import (
    UseCardAction
)

from actions.activate_ability_action import (
    ActivateAbilityAction
)

from core.action_handlers.summon_action_handler import (
    SummonActionHandler
)

from core.action_handlers.destroy_action_handler import (
    DestroyActionHandler
)

from core.action_handlers.proceed_to_attack_step_handler import (
    ProceedToAttackStepHandler,
)

from core.action_handlers.finish_attack_step_handler import (
    FinishAttackStepHandler,
)

from core.action_handlers.cast_spell_action_handler import (
    CastSpellActionHandler
)

from core.action_handlers.attack_action_handler import (
    AttackActionHandler
)

from core.action_handlers.attack_creature_action_handler import (
    AttackCreatureActionHandler
)

from core.action_handlers.use_card_action_handler import (
    UseCardActionHandler
)

from core.action_handlers.activate_ability_action_handler import (
    ActivateAbilityActionHandler
)


class ActionProcessor:

    def __init__(
        self,
        game_controller,
        action_validator=None,
    ):

        self.game_controller = (
            game_controller
        )

        self.validator = (
            action_validator
            or game_controller.action_validator
        )

        self.handlers = {

            SummonAction:
                SummonActionHandler(
                    game_controller
                ),

            DestroyAction:
                DestroyActionHandler(
                    game_controller
                ),

            DestroyMultipleAction:
                DestroyActionHandler(
                    game_controller
                ),

            ProceedToAttackStepAction:
                ProceedToAttackStepHandler(
                    game_controller
                ),

            FinishAttackStepAction:
                FinishAttackStepHandler(
                    game_controller
                ),

            CastSpellAction:
                CastSpellActionHandler(
                    game_controller
                ),

            AttackAction:
                AttackActionHandler(
                    game_controller
                ),

            AttackCreatureAction:
                AttackCreatureActionHandler(
                    game_controller
                ),

            UseCardAction:
                UseCardActionHandler(
                    game_controller
                ),

            ActivateAbilityAction:
                ActivateAbilityActionHandler(
                    game_controller
                ),
        }

    def process(
        self,
        action,
    ):

        if self.game_controller.state.game_over:
            return

        if not self.validator.validate(
            action
        ):

            print(
                f"Illegal action: "
                f"{action}"
            )

            return

        handler = (
            self.handlers.get(
                type(action)
            )
        )

        if handler is None:

            raise ValueError(
                f"No handler for "
                f"{type(action)}"
            )

        handler.process(action)
