"""
すべてのイベント（Event）の抽象基底クラス。能力がトリガーされる契機となります。
"""

class BaseEvent:

    def __init__(self):
        self.cancelled = False

    def __str__(
        self,
    ):

        return (
            f"{self.__class__.__name__}()"
        )
