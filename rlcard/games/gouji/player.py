"""够级玩家。"""
from .utils import team_id


class GoujiPlayer:

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.team_id = team_id(player_id)
        self.hand: list = []          # Card 列表
        self.played_history: list = []  # 已出牌（累计）

    def remove_cards(self, cards: list) -> None:
        """从手牌中移除指定牌（按 (suit, rank) 匹配第一个）。"""
        for card in cards:
            for i, c in enumerate(self.hand):
                if c.suit == card.suit and c.rank == card.rank:
                    del self.hand[i]
                    break

    def add_cards(self, cards: list) -> None:
        self.hand.extend(cards)
