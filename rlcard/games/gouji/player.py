"""够级玩家。"""
import numpy as np

from .utils import team_id, NUM_RANKS, RANK_INDEX


class GoujiPlayer:

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.team_id = team_id(player_id)
        self.hand = np.zeros(NUM_RANKS, dtype=np.int32)
        self.played_history = np.zeros(NUM_RANKS, dtype=np.int32)

    def remove_cards(self, play) -> None:
        """根据 Play 从手牌向量中扣除。"""
        if play.core_rank >= 0:
            self.hand[play.core_rank] -= play.core_count
        self.hand[RANK_INDEX['2']] -= play.attach_2
        self.hand[RANK_INDEX['BJ']] -= play.attach_BJ
        self.hand[RANK_INDEX['RJ']] -= play.attach_RJ
        self.hand[RANK_INDEX['Y']] -= play.attach_Y

    def add_rank(self, rank: str, count: int = 1) -> None:
        self.hand[RANK_INDEX[rank]] += count
