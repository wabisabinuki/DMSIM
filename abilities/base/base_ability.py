"""
すべての能力（Ability）の基底クラス。イベントマネージャへの登録・解除のインターフェースを提供します。
"""

class BaseAbility:

    def __init__(self):

        self.event_manager = None
        self.active_zones = []

    def register(
        self,
        event_manager,
    ):
        pass

    def unregister(
        self,
        event_manager=None,
    ):
        pass
