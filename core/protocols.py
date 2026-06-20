"""
循環参照を回避し、静的型チェックを通すための型定義プロトコル群。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.game_state import GameState


@runtime_checkable
class PlayableContext(Protocol):
    """アクションを処理する（召喚・破壊・呪文など）"""

    @property
    def action_processor(self):
        ...


@runtime_checkable
class ZoneContext(Protocol):
    """ゾーン間のカード移動"""

    @property
    def card_mover(self):
        ...


@runtime_checkable
class HasGameState(Protocol):
    """ゲーム状態の参照"""

    @property
    def state(self) -> GameState:
        ...


@runtime_checkable
class SpellCastContext(Protocol):
    """呪文解決時の対象選択・参照"""

    @property
    def query(self):
        ...

    @property
    def target_selector(self):
        ...


@runtime_checkable
class EffectContext(Protocol):
    """効果解決時に必要なサービス"""

    @property
    def action_processor(self):
        ...

    @property
    def card_mover(self):
        ...

    @property
    def state(self) -> GameState:
        ...


@runtime_checkable
class TriggerContext(Protocol):
    """トリガー能力の発動"""

    @property
    def trigger_manager(self):
        ...


@runtime_checkable
class ShieldTriggerContext(Protocol):
    """シールドトリガーのキューイング"""

    @property
    def shield_trigger_resolver(self):
        ...


@runtime_checkable
class AbilitySetupContext(
    TriggerContext,
    ShieldTriggerContext,
    Protocol,
):
    """能力登録時に渡すコンテキスト"""

    ...
