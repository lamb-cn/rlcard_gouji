"""够级买3/买4 单元测试。"""
import unittest

from rlcard.games.base import Card
from rlcard.games.gouji.player import GoujiPlayer
from rlcard.games.gouji.buy_phase import execute_buy


def C(suit, rank):
    return Card(suit, rank)


def make_players():
    return [GoujiPlayer(i) for i in range(6)]


class BuyPhaseTest(unittest.TestCase):

    def test_lianbang_free(self):
        """玩家0缺3，从联邦(玩家2)免费拿。"""
        players = make_players()
        players[0].hand = [C('S', '5')]
        players[2].hand = [C('S', '3'), C('H', '3'), C('S', '7')]
        # 让其他玩家也有3，避免他们也成为 buyer
        players[1].hand = [C('D', '3')]
        players[3].hand = [C('C', '3')]
        players[4].hand = [C('S', '4')]
        players[5].hand = [C('H', '4')]
        # 玩家4、5也是buyer，需要先满足
        # 简化：让4、5也有3
        players[4].hand = [C('S', '3'), C('S', '4')]
        players[5].hand = [C('H', '3'), C('H', '4')]

        trades = execute_buy('3', players)
        # 玩家0 应有 1 张 3
        self.assertEqual(sum(1 for c in players[0].hand if c.rank == '3'), 1)
        # 玩家2 应剩 1 张 3 (从 2 → 1)
        self.assertEqual(sum(1 for c in players[2].hand if c.rank == '3'), 1)
        # 玩家0 是从对门玩家3买？不是，玩家3只有1张3 不能卖。看是否从玩家2拿
        # 玩家0 的对门 = 3，但3 只有1张3 (counts=1)，不在 available
        # 优先级检查时，next 候选是 联邦 2 和 4
        # 玩家2、玩家4 都有 1张多余3，先按 priority 顺序：(0+2)%6=2, (0+4)%6=4
        # 所以玩家0从玩家2买
        # 玩家0 ← 玩家2 是联邦（同队），免费
        self.assertEqual(len(trades), 1)
        buyer, seller, rk, cost = trades[0]
        self.assertEqual(buyer, 0)
        self.assertEqual(seller, 2)
        self.assertEqual(rk, '3')
        self.assertIsNone(cost)  # 联邦免费

    def test_non_lianbang_pay_with_2(self):
        """玩家0缺3，对门(玩家3)有多余3 → 用 2 付费。"""
        players = make_players()
        players[0].hand = [C('S', '5'), C('H', '2')]   # 有 1 张 2
        players[3].hand = [C('S', '3'), C('H', '3')]   # 多余 1 张 3
        # 其他玩家都给 1 张 3，避免他们成为 buyer
        for i in (1, 2, 4, 5):
            players[i].hand = [C('S', '3')]

        trades = execute_buy('3', players)
        # 玩家0 应得到 3，失去 2
        self.assertEqual(sum(1 for c in players[0].hand if c.rank == '3'), 1)
        self.assertEqual(sum(1 for c in players[0].hand if c.rank == '2'), 0)
        # 玩家3 应剩 1 张 3，多 1 张 2
        self.assertEqual(sum(1 for c in players[3].hand if c.rank == '3'), 1)
        self.assertEqual(sum(1 for c in players[3].hand if c.rank == '2'), 1)

        # trades
        self.assertEqual(len(trades), 1)
        buyer, seller, rk, cost = trades[0]
        self.assertEqual(buyer, 0)
        self.assertEqual(seller, 3)  # 对门
        self.assertEqual(cost, '2')

    def test_non_lianbang_no_2_use_BJ(self):
        """非联邦买3，无 2 则付小王。"""
        players = make_players()
        players[0].hand = [C('S', '5'), C('', 'BJ')]
        players[3].hand = [C('S', '3'), C('H', '3')]
        for i in (1, 2, 4, 5):
            players[i].hand = [C('S', '3')]

        trades = execute_buy('3', players)
        self.assertEqual(sum(1 for c in players[0].hand if c.rank == 'BJ'), 0)
        self.assertEqual(sum(1 for c in players[3].hand if c.rank == 'BJ'), 1)
        self.assertEqual(trades[0][3], 'BJ')

    def test_non_lianbang_no_2_no_BJ_use_RJ(self):
        players = make_players()
        players[0].hand = [C('S', '5'), C('', 'RJ')]
        players[3].hand = [C('S', '3'), C('H', '3')]
        for i in (1, 2, 4, 5):
            players[i].hand = [C('S', '3')]

        trades = execute_buy('3', players)
        self.assertEqual(trades[0][3], 'RJ')

    def test_non_lianbang_free_when_no_cost(self):
        """非联邦买3，无 2/王/鹰 → 直接免费拿。"""
        players = make_players()
        players[0].hand = [C('S', '5')]
        players[3].hand = [C('S', '3'), C('H', '3')]
        for i in (1, 2, 4, 5):
            players[i].hand = [C('S', '3')]

        trades = execute_buy('3', players)
        self.assertIsNone(trades[0][3])
        # 玩家0 只是多了 1 张 3，没付出代价
        self.assertEqual(sum(1 for c in players[0].hand if c.rank == '3'), 1)

    def test_priority_duimen_first(self):
        """对门有多余，联邦也有多余 → 优先从对门买。"""
        players = make_players()
        players[0].hand = [C('S', '5'), C('H', '2')]
        # 对门 3 和 联邦 2 都有 2 张 3
        players[3].hand = [C('S', '3'), C('H', '3')]
        players[2].hand = [C('S', '3'), C('D', '3')]
        for i in (1, 4, 5):
            players[i].hand = [C('S', '3')]

        trades = execute_buy('3', players)
        # 应该先选对门 3
        self.assertEqual(trades[0][1], 3)

    def test_buy_4_works(self):
        """买 4 走相同流程。"""
        players = make_players()
        players[0].hand = [C('S', '7'), C('H', '2')]   # 缺 4
        players[3].hand = [C('S', '4'), C('H', '4')]   # 多余 1 张 4
        for i in (1, 2, 4, 5):
            players[i].hand = [C('S', '4')]

        trades = execute_buy('4', players)
        self.assertEqual(sum(1 for c in players[0].hand if c.rank == '4'), 1)
        self.assertEqual(trades[0][3], '2')


if __name__ == '__main__':
    unittest.main()
