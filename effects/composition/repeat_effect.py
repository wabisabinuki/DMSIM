"""Repeat a set of effects N times, where N is read from package_context."""

from effects.base.base_effect import BaseEffect


class RepeatEffect(BaseEffect):
    """package_context[count_key]の整数値だけ内側の effects を繰り返す。

    内側の effect が False を返した場合（対象なし・スキップ）は
    その時点で繰り返しを中断する。これにより
    「カード1枚につき1体まで破壊してもよい」の任意停止を自然に表現できる。
    """

    def __init__(
        self,
        effects,
        count_key,
    ):
        super().__init__()
        self.effects = effects
        self.count_key = count_key

    def resolve(self):
        count = self.package_context.get(self.count_key, 0)
        if not isinstance(count, int):
            count = 0

        for _ in range(count):
            if not self._resolve_inner():
                break

        return True

    def _resolve_inner(self):
        for effect in self.effects:
            effect.source_card = self.source_card
            effect.source_info = self.source_info
            effect.trigger_snapshot = self.trigger_snapshot
            effect.package_context = self.package_context
            result = effect.resolve()
            if isinstance(result, bool) and not result:
                return False
        return True
