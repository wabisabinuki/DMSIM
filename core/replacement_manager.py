"""
領域移動などに割り込む置換効果（Replacement Effect）を統括・適用するマネージャ。
"""

from abilities.base.replacement_ability \
    import ReplacementAbility
from ui.card_display import format_card_name
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


class ReplacementManager:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def apply(
        self,
        event,
    ):

        if event.replaced:
            return

        # このイベントに適用できる置換をすべて集める（DM 優先順位 =
        # replacement_priority 降順で収集済み）。
        applicable = [
            ability
            for ability in self.collect_replacements()
            if ability.applies(event)
        ]

        if not applicable:
            return

        self._apply_one(
            event,
            applicable,
        )

    def applicable_replacements(
        self,
        event,
    ):

        if event.replaced:
            return []

        return [
            ability
            for ability in self.collect_replacements()
            if ability.applies(event)
        ]

    def would_replace(
        self,
        event,
    ):

        return bool(
            self.applicable_replacements(event)
        )

    def _apply_one(
        self,
        event,
        applicable,
    ):

        # 同一イベントに置換は 1 度だけ。複数の置換が同時に成立する場合は
        # 影響を受けるプレイヤーがどれを適用するか選ぶ（選んだものが replace を
        # 辞退したら、残りの置換から選び直す）。
        remaining = list(applicable)

        while remaining:
            ability = self._choose_replacement(
                event,
                remaining,
            )
            remaining.remove(ability)

            replaced = ability.replace(event)

            if replaced is False:
                continue

            self._log_replacement_active(ability)
            event.replaced = True
            return

    def _choose_replacement(
        self,
        event,
        remaining,
    ):

        # 候補が 1 つ、または選択者を決められない場合は優先順位順の先頭を使う
        # （＝従来挙動）。
        if len(remaining) == 1:
            return remaining[0]

        chooser = self._affected_player(event)
        choice_manager = getattr(
            self.context,
            "choice_manager",
            None,
        )
        if chooser is None or choice_manager is None:
            return remaining[0]

        options = [
            _ReplacementChoice(ability)
            for ability in remaining
        ]
        selected = choice_manager.select(
            chooser,
            options,
            "適用する置換効果を選んでください",
        )

        if isinstance(selected, _ReplacementChoice):
            return selected.ability

        for option in options:
            if option == selected:
                return option.ability

        return remaining[0]

    def _affected_player(
        self,
        event,
    ):

        return (
            getattr(event, "owner", None)
            or getattr(event, "player", None)
        )

    def collect_replacements(
        self,
    ):

        abilities = []

        for player in (
            self.context.state.players
        ):

            zones = [

                player.hand,
                player.battle_zone,
                player.mana_zone,
                player.graveyard,
                player.shield_zone,

            ]

            for zone in zones:

                for card in zone.cards:

                    if (
                        is_card_pending(card)
                        or is_seal_card(card)
                        or is_ignored_by_seal(card)
                    ):
                        continue

                    # 裏向きシールドのカードの置換を「どのゾーンで働くか」は
                    # 各能力が自分で判定する（JsonReplacementAbility は active_zones
                    # 既定 [BATTLE] で、城・G城やシールド・ゴーは active_zones や
                    # shield_face_up 条件で）。ここではゾーンによる一律除外はせず、
                    # 全ゾーンの置換能力を収集して applies() に委ねる。
                    for ability in (
                        card.abilities
                    ):

                        if isinstance(
                            ability,
                            ReplacementAbility,
                        ):

                            abilities.append(
                                ability
                            )

        return sorted(
            abilities,
            key=lambda ability: getattr(
                ability,
                "replacement_priority",
                0,
            ),
            reverse=True,
        )

    def finalize_pending_replacements(
        self,
    ):

        for ability in self.collect_replacements():
            finalize = getattr(
                ability,
                "finalize_pending_replacements",
                None,
            )

            if finalize is not None:
                finalize()

    def _log_replacement_active(
        self,
        ability,
    ):

        owner_card = getattr(
            ability,
            "owner_card",
            None,
        )
        label = self._replacement_label(
            ability
        )

        if owner_card is None:
            print(
                f"置換効果アクティブ: {label}"
            )
            return

        print(
            f"置換効果アクティブ: "
            f"{format_card_name(owner_card)} | {label}"
        )

    def _replacement_label(
        self,
        ability,
    ):

        explicit = getattr(
            ability,
            "replacement_label",
            None,
        )
        if explicit:
            return str(explicit)

        label = getattr(
            ability,
            "label",
            None,
        )
        if label:
            return str(label)

        return type(ability).__name__


class _ReplacementChoice:
    """置換効果の選択肢ラッパ。choice_manager に読みやすいラベルを渡す。"""

    def __init__(
        self,
        ability,
    ):
        self.ability = ability

    @property
    def label(
        self,
    ):
        explicit = getattr(
            self.ability,
            "replacement_label",
            None,
        )
        if explicit:
            return str(explicit)

        owner_card = getattr(
            self.ability,
            "owner_card",
            None,
        )
        if owner_card is not None:
            return getattr(
                owner_card,
                "name",
                type(self.ability).__name__,
            )

        return type(self.ability).__name__

    def __str__(
        self,
    ):
        return self.label
