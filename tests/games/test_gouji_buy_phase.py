"""够级买3/买4 单元测试。"""
import unittest

import numpy as np

from rlcard.games.gouji.player import GoujiPlayer
from rlcard.games.gouji.dealer import GoujiDealer
from rlcard.games.gouji.utils import RANK_INDEX, NUM_RANKS


def make_players():
    return [GoujiPlayer(i) for i in range(6)]


def set_hand(player, counts: dict):
    """用 {rank: count} 设置玩家手牌。"""
    player.hand = np.zeros(NUM_RANKS, dtype=np.int32)
    for r, c in counts.items():
        player.hand[RANK_INDEX[r]] = c


def count_rank(player, rank):
    return int(player.hand[RANK_INDEX[rank]])


def execute_buy(rank, players):
    """测试辅助：创建 dealer 实例执行买牌。"""
    dealer = GoujiDealer(np.random.RandomState(0))
    return dealer._execute_buy(rank, players)


class BuyPhaseTest(unittest.TestCase):

    def test_duimen_first_round(self):
        """所有买家先全员对家交易。"""
        players = make_players()
        set_hand(players[0], {'5': 1, '2': 1})
        set_hand(players[3], {'3': 2})
        for i in (1, 2, 4, 5):
            set_hand(players[i], {'3': 1})

        trades = execute_buy('3', players)
        self.assertEqual(count_rank(players[0], '3'), 1)
        self.assertEqual(count_rank(players[0], '2'), 0)
        self.assertEqual(count_rank(players[3], '3'), 1)
        self.assertEqual(count_rank(players[3], '2'), 1)
        self.assertEqual(len(trades), 1)
        buyer, seller, rk, cost = trades[0]
        self.assertEqual(buyer, 0)
        self.assertEqual(seller, 3)
        self.assertEqual(cost, '2')

    def test_non_lianbang_pay_with_2(self):
        """玩家0缺3，对门(玩家3)有多余3 → 用 2 付费。"""
        players = make_players()
        set_hand(players[0], {'5': 1, '2': 1})
        set_hand(players[3], {'3': 2})
        for i in (1, 2, 4, 5):
            set_hand(players[i], {'3': 1})

        trades = execute_buy('3', players)
        self.assertEqual(count_rank(players[0], '3'), 1)
        self.assertEqual(count_rank(players[0], '2'), 0)
        self.assertEqual(count_rank(players[3], '3'), 1)
        self.assertEqual(count_rank(players[3], '2'), 1)
        self.assertEqual(len(trades), 1)
        buyer, seller, rk, cost = trades[0]
        self.assertEqual(buyer, 0)
        self.assertEqual(seller, 3)
        self.assertEqual(cost, '2')

    def test_non_lianbang_no_2_use_BJ(self):
        players = make_players()
        set_hand(players[0], {'5': 1, 'BJ': 1})
        set_hand(players[3], {'3': 2})
        for i in (1, 2, 4, 5):
            set_hand(players[i], {'3': 1})

        trades = execute_buy('3', players)
        self.assertEqual(count_rank(players[0], 'BJ'), 0)
        self.assertEqual(count_rank(players[3], 'BJ'), 1)
        self.assertEqual(trades[0][3], 'BJ')

    def test_non_lianbang_no_2_no_BJ_use_RJ(self):
        players = make_players()
        set_hand(players[0], {'5': 1, 'RJ': 1})
        set_hand(players[3], {'3': 2})
        for i in (1, 2, 4, 5):
            set_hand(players[i], {'3': 1})

        trades = execute_buy('3', players)
        self.assertEqual(trades[0][3], 'RJ')

    def test_non_lianbang_free_when_no_cost(self):
        players = make_players()
        set_hand(players[0], {'5': 1})
        set_hand(players[3], {'3': 2})
        for i in (1, 2, 4, 5):
            set_hand(players[i], {'3': 1})

        trades = execute_buy('3', players)
        self.assertIsNone(trades[0][3])
        self.assertEqual(count_rank(players[0], '3'), 1)

    def test_buy_4_works(self):
        players = make_players()
        set_hand(players[0], {'7': 1, '2': 1})
        set_hand(players[3], {'4': 2})
        for i in (1, 2, 4, 5):
            set_hand(players[i], {'4': 1})

        trades = execute_buy('4', players)
        self.assertEqual(count_rank(players[0], '4'), 1)
        self.assertEqual(trades[0][3], '2')

    def test_lianbang_second_round(self):
        """对家没多余牌 → 第二轮向联邦买，联邦免费。"""
        players = make_players()
        set_hand(players[0], {'5': 1})
        set_hand(players[2], {'3': 2, '7': 1})   # 联邦多1张3
        set_hand(players[3], {'3': 1})            # 对门只有1张不能卖
        set_hand(players[1], {'3': 1})
        set_hand(players[4], {'3': 1, '4': 1})
        set_hand(players[5], {'3': 1, '4': 1})

        trades = execute_buy('3', players)
        self.assertEqual(count_rank(players[0], '3'), 1)
        self.assertEqual(count_rank(players[2], '3'), 1)
        self.assertEqual(len(trades), 1)
        buyer, seller, rk, cost = trades[0]
        self.assertEqual(buyer, 0)
        self.assertEqual(seller, 2)
        self.assertIsNone(cost)


if __name__ == '__main__':
    unittest.main()
