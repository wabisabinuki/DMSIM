"""
複数のEffectを1つのキュー項目として解決する複合効果。
"""

from effects.base.base_effect import BaseEffect


class PackagedEffect(BaseEffect):
    """
    サブ効果を順番に直接解決する。

    EffectResolverにはこのPackagedEffectだけが積まれるため、
    サブ効果の間に別のEffectを割り込ませない。
    """

    def __init__(
        self,
        effects,
        label=None,
    ):
        super().__init__()

        self.effects = effects
        self.label = label or "PackagedEffect"
        self.package_context = {}
        self.ignore_source_continuity = False

    def can_resolve(
        self,
        game_state,
    ) -> bool:
        if self.ignore_source_continuity:
            return True

        return super().can_resolve(
            game_state
        )

    def resolve(self):
        previous_attempted = True

        for effect in self.effects:
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.trigger_snapshot = self.trigger_snapshot
            effect.condition_context = self.condition_context
            effect.package_context = self.package_context

            connector = getattr(effect, "package_connector", "after")

            if connector == "then" and previous_attempted is not True:
                previous_attempted = None
                continue

            if (
                connector in ("otherwise", "else")
                and previous_attempted is not False
            ):
                previous_attempted = None
                continue

            attempted = self._can_attempt(effect)
            if attempted:
                result = effect.resolve()
                if isinstance(result, bool):
                    attempted = result

            previous_attempted = attempted

            # 状態起因処理（SBA）は各サブ効果の解決ごとに割り込んで適用する。
            # 例: 「マナをすべて手札に戻す」直後にパワー0で破壊され、
            #     その後「手札をすべてマナに置く」が続く、という順序になる。
            # ここで割り込ませるのはルールによる即時処理（破壊など）のみで、
            # キュー上の他のトリガー効果はパッケージ解決後にまとめて処理される。
            self._apply_state_based_actions(effect)

    def _apply_state_based_actions(
        self,
        effect,
    ):
        game = getattr(effect, "game", None)
        if game is None:
            return

        state_based_actions = getattr(
            game,
            "state_based_actions",
            None,
        )
        if state_based_actions is None:
            return

        state_based_actions.check_and_apply()

    def _can_attempt(
        self,
        effect,
    ):
        can_attempt = getattr(
            effect,
            "can_attempt",
            None,
        )

        if can_attempt is None:
            return True

        return can_attempt()

    def __str__(self):
        names = [
            effect.__class__.__name__
            for effect in self.effects
        ]

        return (
            f"{self.label}("
            f"{' -> '.join(names)}"
            ")"
        )
