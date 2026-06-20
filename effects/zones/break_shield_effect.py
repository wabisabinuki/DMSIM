"""Effect that breaks one or more shields."""

from core.effect_argument_resolver import EffectArgumentResolver
from core.shield_break_batch import break_shields_batch, shield_cards_for
from effects.base.base_effect import BaseEffect


class BreakShieldEffect(BaseEffect):

    def __init__(
        self,
        player,
        game,
        amount=1,
        target="opponent_shields",
        optional=True,
        breaker=None,
        exclude=None,
        chooser_player=None,
        prompt="Choose a shield to break",
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.amount = amount
        self.target = target
        self.optional = optional
        # ブレイクの発生源（盾を割る主体）。クリーチャーがブレイクするなど
        # 城以外を発生源にしたい場合に ref で指定する。未指定なら source_card。
        self.breaker = breaker
        # 候補から除外するカード（自分の G城自身など）の ref。
        self.exclude = exclude
        self.chooser_player = chooser_player
        self.prompt = prompt
        self.args = EffectArgumentResolver(game)

    def can_attempt(self):
        return bool(self._shield_options())

    def resolve(self):
        shields = self._shield_options()

        if not shields:
            return False

        chosen = self._choose_shields(shields)
        if not chosen:
            return False

        # 選ばれたシールドを同時ブレイクとしてバッチ処理する
        # （全試行＋置換 → 全通知 → 一括移動）。
        break_shields_batch(
            self.game,
            chosen,
            self._breaker_card(),
        )

        self.game.replacement_manager.finalize_pending_replacements()
        self.game.shield_trigger_resolver.resolve()
        self.game.game_loop.resolve()
        return True

    def _choose_shields(
        self,
        shields,
    ):
        amount = min(
            self._limited_amount(),
            len(shields),
        )

        if amount == 1:
            shield = self.game.target_selector.select(
                self._chooser_player(),
                shields,
                prompt=self.prompt,
                can_skip=self.optional,
            )
            return [] if shield is None else [shield]

        return self.game.target_selector.select_multiple(
            self._chooser_player(),
            shields,
            prompt=self.prompt,
            min_count=amount,
            max_count=amount,
            can_skip=self.optional,
        )

    def _chooser_player(
        self,
    ):
        return self.chooser_player or self.player

    def _limited_amount(
        self,
    ):
        amount = int(self.amount)
        breaker = self._breaker_card()
        if breaker is None:
            return amount

        combat_manager = getattr(
            self.game,
            "combat_manager",
            None,
        )
        break_limits_for = getattr(
            combat_manager,
            "_break_limits_for",
            None,
        )
        if break_limits_for is None:
            return amount

        for limit in break_limits_for(breaker):
            amount = min(
                amount,
                limit,
            )

        return amount

    def _shield_options(self):
        shields = []

        for player in self._target_players():
            shields.extend(
                self._visible_shields(player)
            )

        excluded = self._excluded_cards()
        if excluded:
            shields = [
                shield
                for shield in shields
                if shield not in excluded
            ]

        return shields

    def _breaker_card(self):
        if self.breaker is None:
            return self.source_card

        resolved = self.args.value(
            self.breaker,
            self._context(),
        )
        return resolved if resolved is not None else self.source_card

    def _excluded_cards(self):
        if self.exclude is None:
            return []

        return self.args.cards(
            self.exclude,
            self._context(),
        )

    def _context(self):
        return self.args.context(
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )

    def _visible_shields(
        self,
        player,
    ):

        visible_shields = getattr(
            player.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(player.shield_zone.cards)

    def _target_players(self):
        if self.target == "own_shields":
            return [self.player]

        opponent = self.game.query.get_opponent(
            self.player
        )

        if self.target == "opponent_shields":
            return [opponent]

        if self.target == "shields":
            return [
                self.player,
                opponent,
            ]

        raise ValueError(f"Unknown shield target: {self.target}")
