"""
ターン開始から終了までのステップ進行、マナチャージ制限の解除、アクティブプレイヤーの切り替えなどを管理するマネージャ。
"""

from core.game_step import (
    AttackSubStep,
    GameStep,
)

from actions.proceed_to_attack_step_action import (
    ProceedToAttackStepAction,
)

from actions.finish_attack_step_action import (
    FinishAttackStepAction,
)

from events.turn_event import (
    TurnEndEvent,
    TurnStartEvent,
)

from events.card_state_event import (
    CardUntappedEvent,
)

from zones.zone_type import (
    ZoneType
)

from cards.creature_card import (
    CreatureCard,
)

from abilities.hyper_mode import (
    expire_hyper_modes_for_turn_start,
)

from core.pending_cards import (
    is_card_pending,
    visible_cards,
)
from core.seal_utils import is_ignored_by_seal, is_seal_card


class TurnManager:

    def __init__(
        self,
        context,
        presenter,
    ):

        self.context = context
        self.presenter = presenter
        self.game_state = context.state

        from core.turn_trigger_resolver import (
            TurnTriggerResolver,
        )

        self.turn_triggers = (
            TurnTriggerResolver(context)
        )

    def run_turn(self):

        if self.game_state.game_over:
            return

        player = (
            self.game_state.current_player
        )

        player.has_charged_mana = False

        self.presenter.on_turn_start(
            self.game_state.turn,
            player.name,
            is_extra_turn=self.game_state.is_current_turn_extra,
        )

        self.turn_start_step(player)

        if self._check_game_over():
            return

        self.draw_step(player)

        if self._check_game_over():
            return

        self.mana_charge_step(player)

        if self._check_game_over():
            return

        self.main_step(player)

        if self._check_game_over():
            return

        self.attack_step(player)

        if self._check_game_over():
            return

        self.turn_end_step(player)

    def _check_game_over(self):

        return self.game_state.game_over

    def turn_start_step(
        self,
        player,
    ):

        self.game_state.step = (
            GameStep.TURN_START
        )

        self._clear_summoning_sick(player)

        self._untap_all_cards(player)

        self.context.duration_effect_manager.check_and_cleanup_expired_effects()

        expire_hyper_modes_for_turn_start(
            player,
            self.game_state,
        )

        event = TurnStartEvent(player)

        # 「次の〜ターンのはじめに〜」のような遅延誘発効果や、ターン集計の
        # リセット等はカードのトリガー能力ではなく event_manager の購読者として
        # 登録される。これらにターンイベントを届けてから、カードのターン誘発を
        # 解決する。
        self._notify_non_triggered_subscribers(
            TurnStartEvent,
            event,
        )

        self.turn_triggers.resolve(
            TurnStartEvent,
            event,
            player,
        )

    def _notify_non_triggered_subscribers(
        self,
        event_type,
        event,
    ):
        """ターンイベントを、カードのトリガー能力以外の購読者へ届ける。

        カードの ``TriggeredAbility`` は ``TurnTriggerResolver`` がゾーン・
        ゴースト判定込みで解決するため二重発火を避けて除外する。残りの購読者
        （ターン集計マネージャや「次のターンのはじめに〜」の遅延誘発効果など）に
        だけイベントを配信し、生成された効果をキューから解決する。
        """

        from abilities.base.triggered_ability import TriggeredAbility

        listeners = self.context.event_manager.get_listeners(
            event_type
        )

        notified = False
        for listener in listeners:
            owner = getattr(listener, "__self__", None)
            if isinstance(owner, TriggeredAbility):
                continue

            listener(event)
            notified = True

        if notified:
            self.context.game_loop.resolve()

    def _clear_summoning_sick(
        self,
        player,
    ):

        for creature in (
            player.battle_zone.cards[:]
        ):

            if is_card_pending(creature):
                continue

            if is_seal_card(creature) or is_ignored_by_seal(creature):
                continue

            if isinstance(
                creature,
                CreatureCard,
            ):
                creature.summoning_sick = False

    def _untap_all_cards(
        self,
        player,
    ):

        for card in player.mana_zone.cards:
            was_tapped = card.tapped
            if card.untap(
                player=player,
                turn_start=True,
            ) and was_tapped:
                self.context.event_manager.publish(
                    CardUntappedEvent(
                        player,
                        card,
                        reason="turn_start",
                    )
                )

        for card in (
            player.battle_zone.cards[:]
        ):
            if is_card_pending(card):
                continue

            if is_seal_card(card) or is_ignored_by_seal(card):
                continue

            was_tapped = card.tapped
            if card.untap(
                player=player,
                turn_start=True,
            ) and was_tapped:
                self.context.event_manager.publish(
                    CardUntappedEvent(
                        player,
                        card,
                        reason="turn_start",
                    )
                )

    def draw_step(
        self,
        player,
    ):

        self.game_state.step = GameStep.DRAW

        is_first_player_first_turn = (

            self.game_state.turn == 1

            and

            self.game_state.turn_player_index
            == 0
        )

        if is_first_player_first_turn:
            return

        drew = player.draw(
            self.context.controller,
            1,
        )

        if not drew:
            return

    def mana_charge_step(
        self,
        player,
    ):

        self.game_state.step = (
            GameStep.MANA_CHARGE
        )

        if player.has_charged_mana:
            return

        choices = [None]

        choices.extend(
            visible_cards(
                player.hand.cards
            )
        )

        choice = (
            self.context.choice_manager
            .select(
                player,
                choices,
                "Choose mana charge (skip: 0)",
            )
        )

        if choice is None:
            return

        choice.tapped = (
            choice.is_multicolored()
        )

        self.context.card_mover.move(
            card=choice,
            owner=player,
            from_zone=ZoneType.HAND,
            to_zone=ZoneType.MANA,
            reason="mana_charge",
        )

        player.has_charged_mana = True

        self.presenter.on_mana_charged(
            player.name,
            choice.name,
        )

    def main_step(
        self,
        player,
    ):

        self.game_state.step = GameStep.MAIN

        ctx = self.context

        while True:

            self.presenter.on_main_step_board(
                ctx.state
            )

            actions = (
                ctx.action_generator
                .get_main_step_actions(
                    player
                )
            )

            action = (
                ctx.choice_manager.select(
                    player,
                    actions,
                    "Choose main step action",
                )
            )

            ctx.action_processor.process(
                action
            )

            ctx.game_loop.resolve()

            if self._check_game_over():
                return

            if isinstance(
                action,
                ProceedToAttackStepAction,
            ):
                break

    def attack_step(
        self,
        player,
    ):

        self.game_state.step = GameStep.ATTACK

        ctx = self.context

        while True:

            self.presenter.on_main_step_board(
                ctx.state
            )

            actions = (
                ctx.action_generator
                .get_attack_step_actions(
                    player
                )
            )

            action = (
                ctx.choice_manager.select(
                    player,
                    actions,
                    "Choose attack step action",
                )
            )

            ctx.action_processor.process(
                action
            )

            ctx.game_loop.resolve()

            if self._check_game_over():
                return

            if isinstance(
                action,
                FinishAttackStepAction,
            ):
                break

    def turn_end_step(
        self,
        player,
    ):

        self.game_state.step = GameStep.TURN_END

        self.presenter.on_turn_end_board(
            self.game_state
        )

        event = TurnEndEvent(player)

        self.turn_triggers.resolve(
            TurnEndEvent,
            event,
            player,
        )

        # ニンジャ・ストライクの山札戻しのような「ターンの終わりに」発火する
        # 遅延誘発効果（event_manager の購読者）へも配信する。
        self._notify_non_triggered_subscribers(
            TurnEndEvent,
            event,
        )

        if self._check_game_over():
            return

        # 期間限定効果をチェック・クリーンアップ
        self.context.duration_effect_manager.check_and_cleanup_expired_effects()

        self.context.game_loop.resolve()

        self.advance_turn()

    def advance_turn(self):

        player = (
            self.game_state.current_player
        )

        player.has_charged_mana = False

        self.game_state.attack_sub_step = (
            AttackSubStep.NONE
        )

        self.game_state.advance_to_next_turn()
