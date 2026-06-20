"""
イベント発生時にトリガー能力の発動条件を判定し、条件を満たした効果を即座にEffectResolverキューに追加するマネージャ。
"""

from dataclasses import dataclass

from core.card_snapshot import (
    CardSnapshot,
    EffectSource,
    effect_uses_source_info,
)
from core.condition_context import ConditionContext

from ui.trigger_debug import log_trigger


@dataclass
class PendingTrigger:
    ability: object
    event: object
    source_card: object
    trigger_snapshot: CardSnapshot
    source_info: EffectSource


class TriggerManager:
    """
    Event から Effect を生成するマネージャー

    ライフサイクル:
    1. Ability.on_event() から呼ばれる
    2. CardSnapshot を作成（Trigger 時点のカード状態を保存）
    3. Ability.create_effects(event) で Effect 生成
    4. ConditionContext を作成して Effect に設定
    5. EffectResolver に追加
    """

    def __init__(
        self,
        context,
    ):

        self.context = context
        self.pending_triggers = []

    def process_trigger(
        self,
        ability,
        event,
    ):
        """
        Event に反応して Effect を生成・キューイング

        Args:
            ability: Trigger が成立した Ability
            event: Event
        """

        source_card = (
            ability.owner_card
        )

        # CardSnapshot を作成（Trigger 時点のカード状態を保存）
        trigger_snapshot = CardSnapshot(
            source_card
        )
        source_info = EffectSource(
            source_card,
            game=self.context.controller,
            player=getattr(
                source_card,
                "owner",
                None,
            ),
        )
        pending_trigger = PendingTrigger(
            ability=ability,
            event=event,
            source_card=source_card,
            trigger_snapshot=trigger_snapshot,
            source_info=source_info,
        )

        self.pending_triggers.append(
            pending_trigger
        )
        sentinel = object()
        previous_source_info = getattr(
            ability,
            "_pending_source_info",
            sentinel,
        )
        ability._pending_source_info = source_info
        try:
            # Effect を生成
            effects = (
                ability.create_effects(
                    event
                )
            )
        except Exception:
            if pending_trigger in self.pending_triggers:
                self.pending_triggers.remove(
                    pending_trigger
                )
            raise
        finally:
            if previous_source_info is sentinel:
                if hasattr(
                    ability,
                    "_pending_source_info",
                ):
                    delattr(
                        ability,
                        "_pending_source_info",
                    )
            else:
                ability._pending_source_info = previous_source_info

        log_trigger(
            event,
            ability,
            effects,
        )

        for effect in effects:

            # Effect に source_card を設定
            effect.source_card = (
                source_card
            )
            effect.source_info = source_info

            # Effect に CardSnapshot を設定
            effect.trigger_snapshot = (
                trigger_snapshot
            )
            if effect_uses_source_info(effect):
                effect.ignore_source_continuity = True

            # ConditionContext を作成して設定
            effect.condition_context = (
                ConditionContext(
                    event=event,
                    trigger_snapshot=(
                        trigger_snapshot
                    ),
                    source_info=source_info,
                    game_state=(
                        self.context.state
                    ),
                )
            )

            # Effect を EffectResolver に追加
            # S・トリガーでカードを使う処理自体は
            # ShieldTriggerResolver 側で優先解決する。そこで誘発した
            # 通常の効果は、発生源プレイヤー順の通常キューへ積む。
            self.context\
                .effect_resolver\
                .add_effect(
                    effect,
                    controller=source_card.owner,
                )

        if pending_trigger in self.pending_triggers:
            self.pending_triggers.remove(
                pending_trigger
            )

    def freeze_sources_for(
        self,
        card,
    ):
        self.freeze_sources_for_many(
            [
                card,
            ]
        )

    def freeze_sources_for_many(
        self,
        cards,
    ):
        card_ids = {
            id(card)
            for card in cards
            if card is not None
        }
        if not card_ids:
            return

        for pending in list(
            self.pending_triggers
        ):
            source_info = getattr(
                pending,
                "source_info",
                None,
            )
            source_card = getattr(
                source_info,
                "live_card",
                None,
            )
            if id(source_card) in card_ids:
                source_info.freeze()
