"""
プレイヤーがゲーム中で実行するすべての行動（Action）の抽象基底クラス。
"""

class BaseAction:

    def __init__(self, player):
        self.player = player
