"""够级 Judger 单元测试。"""
import unittest

import numpy as np

from rlcard.games.gouji.judger import GoujiJudger, Play
from rlcard.games.gouji.utils import RANK_INDEX, NUM_RANKS


def parse(ranks):
    return GoujiJudger.parse_play(ranks)


def can_beat(new, cur_play):
    return GoujiJudger.can_beat(new, cur_play)


class ParsePlayTest(unittest.TestCase):

    def test_parse_pure(self):
        p = parse(['7', '7'])
        self.assertEqual(p.core_rank, RANK_INDEX['7'])
        self.assertEqual(p.core_count, 2)
        self.assertEqual(p.attach_2, 0)
        self.assertEqual(p.attach_BJ, 0)
        self.assertEqual(p.attach_RJ, 0)
        self.assertEqual(p.attach_Y, 0)

    def test_parse_attach_2(self):
        # 27777 → core=7777, attach_2=1
        p = parse(['2', '7', '7', '7', '7'])
        self.assertEqual(p.core_rank, RANK_INDEX['7'])
        self.assertEqual(p.core_count, 4)
        self.assertEqual(p.attach_2, 1)
        self.assertEqual(p.total(), 5)

    def test_parse_wang_attach(self):
        # 小王7777 → core=7777, attach_BJ=1
        p = parse(['BJ', '7', '7', '7', '7'])
        self.assertEqual(p.core_count, 4)
        self.assertEqual(p.attach_BJ, 1)

    def test_parse_pure_2(self):
        # 全是 2 → core_rank=2, core_count=2, attach_2=0
        p = parse(['2', '2'])
        self.assertEqual(p.core_rank, RANK_INDEX['2'])
        self.assertEqual(p.core_count, 2)
        self.assertEqual(p.attach_2, 0)

    def test_parse_pure_wang_single_type(self):
        # 三大王 → 王模式下 core_rank=最小王, 数量=0, attach 记录数量
        p = parse(['RJ', 'RJ', 'RJ'])
        self.assertEqual(p.core_rank, RANK_INDEX['RJ'])
        self.assertEqual(p.core_count, 0)
        self.assertEqual(p.attach_RJ, 3)

    def test_parse_pure_wang_eagle(self):
        p = parse(['Y'] * 3)
        self.assertEqual(p.core_rank, RANK_INDEX['Y'])
        self.assertEqual(p.core_count, 0)

    def test_parse_2_with_wang(self):
        # 王22 → core=22, attach_BJ=1
        p = parse(['BJ', '2', '2'])
        self.assertEqual(p.core_rank, RANK_INDEX['2'])
        self.assertEqual(p.core_count, 2)
        self.assertEqual(p.attach_BJ, 1)
        self.assertEqual(p.attach_2, 0)

    def test_invalid_mixed_core(self):
        with self.assertRaises(ValueError):
            parse(['7', '8'])

    def test_pass_play(self):
        p = parse([])
        self.assertTrue(p.is_pass())


class CanBeatTest(unittest.TestCase):

    def test_88888_beats_27777(self):
        cur = parse(['2', '7', '7', '7', '7'])
        new = ['8', '8', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_22888_beats_27777(self):
        cur = parse(['2', '7', '7', '7', '7'])
        new = ['2', '2', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_wang2888_beats_27777(self):
        cur = parse(['2', '7', '7', '7', '7'])
        new = ['BJ', '2', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_dawang6666_cant_beat_xiaowang7777(self):
        cur = parse(['BJ', '7', '7', '7', '7'])
        new = ['RJ', '6', '6', '6', '6']
        self.assertFalse(can_beat(new, cur))

    def test_xiaowang7777_cant_beat_dawang6666(self):
        cur = parse(['RJ', '6', '6', '6', '6'])
        new = ['BJ', '7', '7', '7', '7']
        self.assertFalse(can_beat(new, cur))

    def test_xiaowang2777_equals_xiaowang7777(self):
        p1 = parse(['BJ', '2', '7', '7', '7'])
        p2 = parse(['BJ', '7', '7', '7', '7'])
        cards1 = ['BJ', '2', '7', '7', '7']
        cards2 = ['BJ', '7', '7', '7', '7']
        self.assertFalse(can_beat(cards1, p2))
        self.assertFalse(can_beat(cards2, p1))

    def test_three_xiaowang_beats_222(self):
        cur = parse(['2', '2', '2'])
        new = ['BJ', 'BJ', 'BJ']
        self.assertTrue(can_beat(new, cur))

    def test_three_dawang_beats_222(self):
        cur = parse(['2', '2', '2'])
        new = ['RJ', 'RJ', 'RJ']
        self.assertTrue(can_beat(new, cur))

    def test_wang22_cant_beat_222(self):
        cur = parse(['2', '2', '2'])
        new = ['BJ', '2', '2']
        self.assertFalse(can_beat(new, cur))

    def test_y_needs_two_to_kill_y(self):
        """1 Y 不能平级杀 Y，需 2 Y 二杀一。"""
        cur = parse(['Y', 'A', 'A', 'A', 'A'])
        new = ['Y', '2', '2', '2', '2']
        self.assertFalse(can_beat(new, cur))

    def test_two_eagle_999_beats_dawang_xiaowang_888(self):
        cur = parse(['RJ', 'BJ', '8', '8', '8'])
        new = ['Y', 'Y', '9', '9', '9']
        self.assertTrue(can_beat(new, cur))

    def test_one_eagle_one_dawang_999_beats_dawang_xiaowang_888(self):
        cur = parse(['RJ', 'BJ', '8', '8', '8'])
        new = ['Y', 'RJ', '9', '9', '9']
        self.assertTrue(can_beat(new, cur))

    def test_xiaowang8888_cant_beat_xiaowang7777(self):
        """1 BJ 不能平级，需 2 BJ 二杀一。"""
        cur = parse(['BJ', '7', '7', '7', '7'])
        new = ['BJ', '8', '8', '8', '8']
        self.assertFalse(can_beat(new, cur))

    def test_total_mismatch_cant_beat(self):
        """无王时核心点数大但张数不同，不能压（恰好匹配）。"""
        cur = parse(['7', '7'])
        new = ['8', '8', '8']
        self.assertFalse(can_beat(new, cur))

    def test_accept_play_arg(self):
        """can_beat 兼容 Play 型参。"""
        cur = parse(['7', '7'])
        new_play = parse(['8', '8'])
        self.assertTrue(can_beat(new_play, cur))

    def test_play_arg_pass_returns_false(self):
        cur = parse(['7', '7'])
        from rlcard.games.gouji.judger import PASS_PLAY
        self.assertFalse(can_beat(PASS_PLAY, cur))


class WangKillTest(unittest.TestCase):
    """王杀规则：二杀一、三杀一。"""

    def test_two_xiaowang_kill_one_xiaowang(self):
        """2 BJ 杀 1 BJ（平级二杀一）。"""
        cur = parse(['BJ', '7', '7', '7', '7'])
        new = ['BJ', 'BJ', '8', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_three_xiaowang_kill_one_dawang(self):
        """3 BJ 杀 1 RJ（越级三杀一）。"""
        cur = parse(['RJ', '7', '7', '7', '7'])
        new = ['BJ', 'BJ', 'BJ', '8', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_user_example_rjrjbj888_beats_rj7777(self):
        """用户例子：RJ RJ BJ 888 杀 RJ 7777。
        2 RJ 二杀一覆盖 1 RJ，核心 888 > 7777。
        """
        cur = parse(['RJ', '7', '7', '7', '7'])
        new = ['RJ', 'RJ', 'BJ', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_three_bj_cant_kill_y(self):
        """3 BJ 不能杀 1 Y（小王不杀鹰）。"""
        cur = parse(['Y', '7', '7', '7', '7'])
        new = ['BJ', 'BJ', 'BJ', '8', '8', '8', '8']
        # 3 BJ: lower=RJ(14), cur=Y(15), gap=1, 三杀一成立
        # 但 BJ(13) != RJ(14)，不能三杀一
        # 实际上 lower=14(RJ), need 3 RJ, but we have BJ. Tricky.
        # 重点是 3 BJ(13) 不能杀 Y(15)，因为 BJ ≠ Y-1=RJ
        self.assertFalse(can_beat(new, cur))

    def test_three_rj_kill_one_y(self):
        """3 RJ 杀 1 Y（越级三杀一 RJ→Y）。"""
        cur = parse(['Y', '7', '7', '7', '7'])
        new = ['RJ', 'RJ', 'RJ', '8', '8', '8', '8']
        self.assertTrue(can_beat(new, cur))

    def test_two_rj_kill_one_rj_extra_bj_fails(self):
        """2 RJ 杀 1 RJ，多余 1 BJ 无处消耗 → 不能恰好压。"""
        cur = parse(['RJ', '7', '7', '7', '7'])
        new = ['RJ', 'RJ', 'BJ', '8', '8', '8', '8']
        self.assertFalse(can_beat(new, cur))

    def test_mixed_kill_rjrbj_needs_more_wangs(self):
        """2 RJ 二杀一 RJ 后剩 1 BJ，无法覆盖 1 BJ（需平级已删除）。"""
        cur = parse(['RJ', 'BJ', '7', '7', '7'])
        new = ['RJ', 'RJ', 'BJ', '8', '8', '8']
        self.assertFalse(can_beat(new, cur))

    def test_xiaowang_needs_two_to_kill_one(self):
        """1 BJ 不能平级，需 2 BJ 二杀一才可压 1 BJ。"""
        cur = parse(['BJ', '7', '7', '7', '7'])
        new = ['BJ', '8', '8', '8', '8']
        self.assertFalse(can_beat(new, cur))


class IsGoujiTest(unittest.TestCase):

    def test_thresholds(self):
        p = parse(['T'] * 5)
        self.assertTrue(p.is_gouji())
        p = parse(['J'] * 4)
        self.assertTrue(p.is_gouji())
        p = parse(['2'])
        self.assertTrue(p.is_gouji())
        p = parse(['T', 'T'])
        self.assertFalse(p.is_gouji())
        p = parse(['BJ', '3'])
        self.assertTrue(p.is_gouji())

    def test_attach_2_counts_for_threshold(self):
        p = parse(['2', '2', 'T', 'T', 'T'])
        self.assertTrue(p.is_gouji())


class ConstraintsTest(unittest.TestCase):

    def _hand(self, counts: dict) -> np.ndarray:
        h = np.zeros(NUM_RANKS, dtype=np.int32)
        for r, c in counts.items():
            h[RANK_INDEX[r]] = c
        return h

    def test_three_must_be_last(self):
        valid = GoujiJudger.is_valid_play_with_constraints
        # 只剩 3+5 时出 3 → 不合法
        hand = self._hand({'3': 1, '5': 1})
        self.assertFalse(valid(['3'], hand))
        # 只剩 1 张 3 → 合法
        hand = self._hand({'3': 1})
        self.assertTrue(valid(['3'], hand))
        # 出多张 3 也不合法
        hand = self._hand({'3': 2})
        self.assertFalse(valid(['3', '3'], hand))

    def test_four_must_all_at_once(self):
        valid = GoujiJudger.is_valid_play_with_constraints
        hand = self._hand({'4': 3, '5': 1})
        self.assertFalse(valid(['4'], hand))
        self.assertTrue(valid(['4', '4', '4'], hand))

    def test_four_no_attach(self):
        valid = GoujiJudger.is_valid_play_with_constraints
        hand = self._hand({'4': 2, '2': 1, 'BJ': 1})
        self.assertFalse(valid(['4', '4', '2'], hand))
        self.assertFalse(valid(['4', '4', 'BJ'], hand))
        self.assertTrue(valid(['4', '4'], hand))


class PayoffTest(unittest.TestCase):

    def test_simple_payoffs(self):
        from rlcard.games.gouji.player import GoujiPlayer
        players = [GoujiPlayer(i) for i in range(6)]
        # 前三人不全是同队：正常结算
        finish = [0, 3, 2, 1, 4, 5]
        # 0=team0第1(+4), 3=team1第2(+2), 2=team0第3(0), 1=team1第4(0), 4=team0第5(-2), 5=team1第6(-4)
        # team0: 4+0-2=2, /3≈0.67; team1: 2+0-4=-2, /3≈-0.67
        payoffs = GoujiJudger.judge_payoffs(players, finish)
        self.assertAlmostEqual(payoffs[0], 2.0 / 3)
        self.assertAlmostEqual(payoffs[2], 2.0 / 3)
        self.assertAlmostEqual(payoffs[4], 2.0 / 3)
        self.assertAlmostEqual(payoffs[1], -2.0 / 3)
        self.assertAlmostEqual(payoffs[3], -2.0 / 3)
        self.assertAlmostEqual(payoffs[5], -2.0 / 3)


class PlayArrayTest(unittest.TestCase):

    def test_to_array_and_back(self):
        p = Play(core_rank=4, core_count=3, attach_2=1,
                 attach_BJ=0, attach_RJ=0, attach_Y=0)
        arr = p.to_array()
        self.assertEqual(arr.shape, (6,))
        self.assertEqual(arr[0], 4)
        self.assertEqual(arr[1], 3)
        self.assertEqual(arr[2], 1)

        p2 = Play.from_array(arr)
        self.assertEqual(p2.core_rank, 4)
        self.assertEqual(p2.core_count, 3)
        self.assertEqual(p2.attach_2, 1)

    def test_pass_play_array(self):
        from rlcard.games.gouji.judger import PASS_PLAY
        self.assertTrue(PASS_PLAY.is_pass())
        arr = PASS_PLAY.to_array()
        self.assertEqual(arr[0], -1)


if __name__ == '__main__':
    unittest.main()
