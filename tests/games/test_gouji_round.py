"""够级 Round 状态机单元测试。"""
import unittest

from rlcard.games.base import Card
from rlcard.games.gouji.round import GoujiRound, PlayerRoundStatus
from rlcard.games.gouji.judger import GoujiJudger


def C(suit, rank):
    return Card(suit, rank)


def parse(cards):
    return GoujiJudger.parse_play(cards)


class RoundBasicTest(unittest.TestCase):

    def test_initial_state(self):
        rs = GoujiRound(leader_id=0)
        self.assertEqual(rs.current_player_id, 0)
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.LEADING)
        for i in range(1, 6):
            self.assertEqual(rs.player_status[i], PlayerRoundStatus.ACTIVE)
        self.assertIsNone(rs.last_play)

    def test_leader_plays_then_next_is_active(self):
        rs = GoujiRound(leader_id=0)
        cards = [C('S', '7'), C('H', '7')]
        play = parse(cards)
        over = rs.proceed('77', play)
        self.assertFalse(over)
        # 玩家0 PLAYED，下一玩家逆时针 = 5
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.PLAYED)
        self.assertEqual(rs.current_player_id, 5)

    def test_pass_marks_passed(self):
        rs = GoujiRound(leader_id=0)
        rs.proceed('77', parse([C('S', '7'), C('H', '7')]))
        # 玩家5 过牌
        rs.proceed('pass', None)
        self.assertEqual(rs.player_status[5], PlayerRoundStatus.PASSED)


class YieldTest(unittest.TestCase):

    def test_yield_then_others_play_yield_becomes_pass(self):
        """让牌后任何人出牌 → 让牌自动变过牌。"""
        rs = GoujiRound(leader_id=0)
        # 玩家0 出 77
        rs.proceed('77', parse([C('S', '7'), C('H', '7')]))
        # 当前玩家5；玩家5 让牌（5 与 0 同队联邦）
        # 等等，0 是队0，5 是队1，不是联邦。改成手动
        rs.current_player_id = 4  # 玩家4 是队0 同队
        rs.proceed('yield', None)
        self.assertEqual(rs.player_status[4], PlayerRoundStatus.YIELDED)

        # 现在玩家3 出 88（更大）
        rs.current_player_id = 3
        rs.player_status[3] = PlayerRoundStatus.ACTIVE
        rs.proceed('88', parse([C('S', '8'), C('H', '8')]))
        # 玩家4 的 YIELDED 应变成 PASSED
        self.assertEqual(rs.player_status[4], PlayerRoundStatus.PASSED)

    def test_yield_resolves_to_active_when_no_one_beats(self):
        """让牌后所有非让牌都 PASSED → 让牌玩家重新可决策。

        让 leader=2, 玩家2 出 77，玩家1 过, 玩家0(联邦) 让, 玩家5 过, 玩家4 过, 玩家3 过
        → 此时玩家0 应被允许重新决策（YIELDED 仍存在）
        """
        rs = GoujiRound(leader_id=2)
        rs.proceed('77', parse([C('S', '7'), C('H', '7')]))   # P2 出
        # 当前应是 P1
        self.assertEqual(rs.current_player_id, 1)
        rs.proceed('pass', None)                               # P1 过
        self.assertEqual(rs.current_player_id, 0)
        rs.proceed('yield', None)                              # P0 让（与P2同队）
        # 当前应是 P5
        self.assertEqual(rs.current_player_id, 5)
        rs.proceed('pass', None)                               # P5 过
        rs.proceed('pass', None)                               # P4 过
        rs.proceed('pass', None)                               # P3 过
        # 现在所有非 yield 都 passed，让牌玩家 P0 应能继续行动
        self.assertEqual(rs.current_player_id, 0)
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.YIELDED)


class GoujiExceptionTest(unittest.TestCase):
    """过牌后的够级牌例外。"""

    def test_exception_A_duimen_plays_gouji_reactivates(self):
        """例外A：对门出够级牌 → PASSED 玩家变 ACTIVE。"""
        rs = GoujiRound(leader_id=2)
        # P2 出 77
        rs.proceed('77', parse([C('S', '7'), C('H', '7')]))
        # P1 过；P0 过
        rs.proceed('pass', None)
        rs.proceed('pass', None)
        # 此时 P0 是 PASSED
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.PASSED)

        # P5 出 88（也是普通牌，不是够级）
        rs.proceed('88', parse([C('S', '8'), C('H', '8')]))
        # P0 应仍 PASSED
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.PASSED)

        # 跳到 P3，P3 是 P0 的对门
        rs.current_player_id = 3
        rs.player_status[3] = PlayerRoundStatus.ACTIVE
        # P3 出 5×T 这种够级牌
        gouji_cards = [C(s, 'T') for s in 'SHDC'] + [C('S', 'T')]
        rs.proceed('TTTTT', parse(gouji_cards))
        # P0 (对门) 应被重新激活
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.ACTIVE)

    def test_exception_B_duimen_play_unbeaten(self):
        """例外B：对门牌其他人均 PASSED → P 重新 ACTIVE。"""
        rs = GoujiRound(leader_id=3)
        # P3 出 77（P3 是 P0 的对门）
        rs.proceed('77', parse([C('S', '7'), C('H', '7')]))
        # P2 过
        rs.proceed('pass', None)
        # P1 过
        rs.proceed('pass', None)
        # 当前 P0
        self.assertEqual(rs.current_player_id, 0)
        # P0 过（先过一下）
        rs.proceed('pass', None)
        # 当前 P5
        rs.proceed('pass', None)
        # 当前 P4
        rs.proceed('pass', None)
        # 此时除 P3、P0 外其他人都 PASSED
        # 例外B 应在 _advance_turn 中重启 P0
        # P0 的 status 应变为 ACTIVE
        self.assertEqual(rs.player_status[0], PlayerRoundStatus.ACTIVE)


class RoundEndTest(unittest.TestCase):

    def test_round_ends_when_all_passed(self):
        """leader 出牌，其他人都过牌 → 本轮结束。"""
        rs = GoujiRound(leader_id=0)
        # P0 出
        rs.proceed('77', parse([C('S', '7'), C('H', '7')]))
        # 5 个人都过
        over = False
        for _ in range(5):
            over = rs.proceed('pass', None)
        self.assertTrue(over)


if __name__ == '__main__':
    unittest.main()
