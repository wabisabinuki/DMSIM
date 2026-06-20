"""
各種アクションハンドラの抽象基底クラス。
"""

class BaseActionHandler:

    def __init__(
        self,
        game_controller,
    ):

        self.game_controller = (
            game_controller
        )
