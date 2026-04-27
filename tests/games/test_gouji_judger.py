"""够级 Judger 单元测试。"""
import unittest

from rlcard.games.base import Card
from rlcard.games.gouji.judger import GoujiJudger, Play
from rlcard.games.gouji.utils import RANK_INDEX


def C(suit, rank):
    return Card(suit, rank)


def parse(cards):
    return GoujiJudger.parse_play(cards)


def can_beat(new, cur_play):
    return GoujiJudger.can_beat(new, cur_play)


class ParsePlayTest(unittest.TestCase):

    def test_parse_pure(self):
        p = parse([C('S', '7'), C('H', '7')])
        self.assertEqual(p.core_rank, RANK_INDEX['7'])
        self.assertEqual(p.core_count, 2)
        self.assertEqual(p.attach_2, 0)
        self.assertEqual(p.attach_BJ, 0)
        self.assertEqual(p.attach_RJ, 0)
        self.assertEqual(p.attach_Y, 0)

    def test_parse_attach_2(self):
        # 27777 → core=7777, attach_2=1
        p = parse([C('S', '2'), C('S', '7'), C('H', '7'),
                   C('D', '7'), C('C', '7')])
        self.assertEqual(p.core_rank, RANK_INDEX['7'])
        self.assertEqual(p.core_count, 4)
        self.assertEqual(p.attach_2, 1)
        self.assertEqual(p.total(), 5)

    def test_parse_wang_attach(self):
        # 小王7777 → core=7777, attach_BJ=1
        p = parse([C('', 'BJ'), C('S', '7'), C('H', '7'),
                   C('D', '7'), C('C', '7')])
        self.assertEqual(p.core_count, 4)
        self.assertEqual(p.attach_BJ, 1)

    def test_parse_pure_2(self):
        # 全是 2 → 纯core，core_rank=2
        p = parse([C('S', '2'), C('H', '2')])
        self.assertEqual(p.core_rank, RANK_INDEX['2'])
        self.assertEqual(p.core_count, 2)
        self.assertEqual(p.attach_2, 0)

    def test_parse_pure_wang_single_type(self):
        # 三大王 → 纯core
        p = parse([C('', 'RJ'), C('', 'RJ'), C('', 'RJ')])
        self.assertEqual(p.core_rank, RANK_INDEX['RJ'])
        self.assertEqual(p.core_count, 3)
        self.assertEqual(p.attach_RJ, 0)

    def test_parse_pure_wang_eagle(self):
        p = parse([C('', 'Y')] * 3)
        self.assertEqual(p.core_rank, RANK_INDEX['Y'])
        self.assertEqual(p.core_count, 3)

    def test_parse_2_with_wang(self):
        # 王22 → core=22, attach_BJ=1
        p = parse([C('', 'BJ'), C('S', '2'), C('H', '2')])
        self.assertEqual(p.core_rank, RANK_INDEX['2'])
        self.assertEqual(p.core_count, 2)
        self.assertEqual(p.attach_BJ, 1)
        self.assertEqual(p.attach_2, 0)

    def test_invalid_mixed_core(self):
        with self.assertRaises(ValueError):
            parse([C('S', '7'), C('H', '8')])

    def test_invalid_pure_mixed_wangs(self):
        with self.assertRaises(ValueError):
            parse([C('', 'BJ'), C('', 'RJ')])

    def test_pass_play(self):
        p = parse([])
        self.assertTrue(p.is_pass)


class CanBeatTest(unittest.TestCase):
    """基于 PDF 例子和用户确认的关键例子。"""

    def test_88888_beats_27777(self):
        cur = parse([C('S', '2')] + [C(s, '7') for s in 'SHDC'])
        new = [C(s, '8') for s in 'SHDC'] + [C('S', '8')]
        self.assertTrue(can_beat(new, cur))

    def test_22888_beats_27777(self):
        cur = parse([C('S', '2')] + [C(s, '7') for s in 'SHDC'])
        new = [C('S', '2'), C('H', '2'),
               C('S', '8'), C('H', '8'), C('D', '8')]
        self.assertTrue(can_beat(new, cur))

    def test_wang2888_beats_27777(self):
        cur = parse([C('S', '2')] + [C(s, '7') for s in 'SHDC'])
        new = [C('', 'BJ'), C('S', '2'),
               C('S', '8'), C('H', '8'), C('D', '8')]
        self.assertTrue(can_beat(new, cur))

    def test_dawang6666_cant_beat_xiaowang7777(self):
        # 用户例1：core 更小则不能压
        cur = parse([C('', 'BJ')] + [C(s, '7') for s in 'SHDC'])
        new = [C('', 'RJ')] + [C(s, '6') for s in 'SHDC']
        self.assertFalse(can_beat(new, cur))

    def test_xiaowang7777_cant_beat_dawang6666(self):
        # 用户例1反向：王覆盖失败
        cur = parse([C('', 'RJ')] + [C(s, '6') for s in 'SHDC'])
        new = [C('', 'BJ')] + [C(s, '7') for s in 'SHDC']
        self.assertFalse(can_beat(new, cur))

    def test_xiaowang2777_equals_xiaowang7777(self):
        # 用户例2：互不能压
        p1 = parse([C('', 'BJ'), C('S', '2'),
                    C('S', '7'), C('H', '7'), C('D', '7')])
        p2 = parse([C('', 'BJ'),
                    C('S', '7'), C('H', '7'), C('D', '7'), C('C', '7')])
        cards1 = [C('', 'BJ'), C('S', '2'),
                  C('S', '7'), C('H', '7'), C('D', '7')]
        cards2 = [C('', 'BJ'),
                  C('S', '7'), C('H', '7'), C('D', '7'), C('C', '7')]
        self.assertFalse(can_beat(cards1, p2))
        self.assertFalse(can_beat(cards2, p1))

    def test_three_xiaowang_beats_222(self):
        # 用户例3
        cur = parse([C('S', '2'), C('H', '2'), C('D', '2')])
        new = [C('', 'BJ'), C('', 'BJ'), C('', 'BJ')]
        self.assertTrue(can_beat(new, cur))

    def test_three_dawang_beats_222(self):
        cur = parse([C('S', '2'), C('H', '2'), C('D', '2')])
        new = [C('', 'RJ'), C('', 'RJ'), C('', 'RJ')]
        self.assertTrue(can_beat(new, cur))

    def test_wang22_cant_beat_222(self):
        # 用户例3关键：core 必须严格大
        cur = parse([C('S', '2'), C('H', '2'), C('D', '2')])
        new = [C('', 'BJ'), C('S', '2'), C('H', '2')]
        self.assertFalse(can_beat(new, cur))

    def test_eagle_unbeatable(self):
        # 鹰挂的不可被压
        cur = parse([C('', 'Y')] + [C(s, 'A') for s in 'SHDC'])
        new = [C('', 'Y')] + [C(s, '2') for s in 'SHDC']
        self.assertFalse(can_beat(new, cur))

    def test_two_eagle_999_beats_dawang_xiaowang_888(self):
        cur = parse([C('', 'RJ'), C('', 'BJ'),
                     C('S', '8'), C('H', '8'), C('D', '8')])
        new = [C('', 'Y'), C('', 'Y'),
               C('S', '9'), C('H', '9'), C('D', '9')]
        self.assertTrue(can_beat(new, cur))

    def test_one_eagle_one_dawang_999_beats_dawang_xiaowang_888(self):
        cur = parse([C('', 'RJ'), C('', 'BJ'),
                     C('S', '8'), C('H', '8'), C('D', '8')])
        new = [C('', 'Y'), C('', 'RJ'),
               C('S', '9'), C('H', '9'), C('D', '9')]
        self.assertTrue(can_beat(new, cur))

    def test_xiaowang8888_beats_xiaowang7777(self):
        cur = parse([C('', 'BJ')] + [C(s, '7') for s in 'SHDC'])
        new = [C('', 'BJ')] + [C(s, '8') for s in 'SHDC']
        self.assertTrue(can_beat(new, cur))

    def test_total_mismatch_cant_beat(self):
        cur = parse([C('S', '7'), C('H', '7')])
        new = [C('S', '8'), C('H', '8'), C('D', '8')]
        self.assertFalse(can_beat(new, cur))


class IsGoujiTest(unittest.TestCase):

    def test_thresholds(self):
        # 5个10
        p = parse([C(s, 'T') for s in 'SHDC'] + [C('S', 'T')])
        self.assertTrue(p.is_gouji())
        # 4个J
        p = parse([C(s, 'J') for s in 'SHDC'])
        self.assertTrue(p.is_gouji())
        # 1个2
        p = parse([C('S', '2')])
        self.assertTrue(p.is_gouji())
        # 2个10 不够
        p = parse([C('S', 'T'), C('H', 'T')])
        self.assertFalse(p.is_gouji())
        # 含挂画
        p = parse([C('', 'BJ'), C('S', '3')])
        self.assertTrue(p.is_gouji())

    def test_attach_2_counts_for_threshold(self):
        # 22TTT → 视为五个10 → 是够级
        p = parse([C('S', '2'), C('H', '2'),
                   C('S', 'T'), C('H', 'T'), C('D', 'T')])
        self.assertTrue(p.is_gouji())


class ConstraintsTest(unittest.TestCase):
    """3 / 4 的特殊出牌约束。"""

    def test_three_must_be_last(self):
        valid = GoujiJudger.is_valid_play_with_constraints
        # 只剩 3+5 时出 3 → 不合法
        hand = [C('S', '3'), C('H', '5')]
        self.assertFalse(valid([C('S', '3')], hand))
        # 只剩 1 张 3 → 合法
        self.assertFalse(valid([C('S', '3'), C('H', '3')],
                                [C('S', '3'), C('H', '3')]))  # 出多张3也不合法
        self.assertTrue(valid([C('S', '3')], [C('S', '3')]))

    def test_four_must_all_at_once(self):
        valid = GoujiJudger.is_valid_play_with_constraints
        hand = [C('S', '4'), C('H', '4'), C('D', '4'), C('S', '5')]
        # 仅出 1 张 4 → 不合法
        self.assertFalse(valid([C('S', '4')], hand))
        # 全出 3 张 4 → 合法
        self.assertTrue(valid(
            [C('S', '4'), C('H', '4'), C('D', '4')], hand))

    def test_four_no_attach(self):
        valid = GoujiJudger.is_valid_play_with_constraints
        hand = [C('S', '4'), C('H', '4'),
                C('S', '2'), C('', 'BJ')]
        # 4444 + 2 贴 → 不合法
        self.assertFalse(valid(
            [C('S', '4'), C('H', '4'), C('S', '2')], hand))
        # 4444 + 王 → 不合法
        self.assertFalse(valid(
            [C('S', '4'), C('H', '4'), C('', 'BJ')], hand))
        # 4 全出且不挂 → 合法
        self.assertTrue(valid(
            [C('S', '4'), C('H', '4')], hand))


class PayoffTest(unittest.TestCase):

    def test_team0_wins(self):
        payoffs = GoujiJudger.judge_payoffs(0, 6)
        self.assertEqual(list(payoffs), [1.0, -1.0, 1.0, -1.0, 1.0, -1.0])

    def test_team1_wins(self):
        payoffs = GoujiJudger.judge_payoffs(1, 6)
        self.assertEqual(list(payoffs), [-1.0, 1.0, -1.0, 1.0, -1.0, 1.0])


if __name__ == '__main__':
    unittest.main()
