"""
パワー増減など、カードの状態を修飾する修飾子の抽象基底クラス。
"""

class BaseModifier:

    def __init__(self):

        self.expired = False
