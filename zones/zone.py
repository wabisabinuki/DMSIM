"""
手札、マナ、シールド、バトルゾーンなどの具体的なカード領域クラス。カードの一覧管理と追加・削除を行います。
"""

# zones/zone.py

class Zone:
    def __init__(self, name):
        self.name = name
        self.cards = []

    def add(self, card):
        self.cards.append(card)

    def remove(self, card):
        self.cards.remove(card)

    def top(self):
        return self.cards[0]
    
    def is_empty(self):
        return len(self.cards) == 0

    def pop_top(self):
        return self.cards.pop(0)

    def __len__(self):
        return len(self.cards)
    
    def __iter__(self):
        return iter(self.cards)
