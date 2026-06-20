"""
ルール収束型エンジンの心臓部。状態定義処理（SBA）の判定と効果解決（Effect.resolve）を状態が変化しなくなるまで反復するループ処理。
"""

class GameLoop:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def resolve(
        self,
    ):

        ctx = self.context
        if ctx.state.game_over:
            return

        if ctx.resolving:
            return

        ctx.resolving = True

        while True:

            if ctx.state.game_over:
                break

            # SBA優先
            changed = (
                ctx.state_based_actions
                .check_and_apply()
            )

            if ctx.state.game_over:
                break

            if changed:
                continue

            # effect
            if (
                ctx.effect_resolver
                .has_effects()
            ):

                ctx.effect_resolver\
                    .resolve_next(ctx)

                continue

            break

        ctx.resolving = False
