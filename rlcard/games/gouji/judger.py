"""够级牌型解析与比牌核心。"""
from dataclasses import dataclass
from itertools import combinations
from typing import Optional, Union

import numpy as np

from .utils import (
    RANK_INDEX, RANK_STR, ATTACH_RANKS, WANG_RANKS,
    is_duimen,
)


@dataclass
class Play:
    """一次出牌的结构化解析结果。

    core_rank: 0-15 (RANK_INDEX), -1 = pass
    """
    core_rank: int
    core_count: int
    attach_2: int
    attach_BJ: int
    attach_RJ: int
    attach_Y: int

    # ── 张量互转 ──

    def to_array(self) -> np.ndarray:
        """6-dim float32 张量"""
        return np.array([
            self.core_rank, self.core_count,
            self.attach_2, self.attach_BJ,
            self.attach_RJ, self.attach_Y,
        ], dtype=np.float32)

    @staticmethod
    def from_array(arr: np.ndarray) -> 'Play':
        return Play(
            core_rank=int(arr[0]), core_count=int(arr[1]),
            attach_2=int(arr[2]), attach_BJ=int(arr[3]),
            attach_RJ=int(arr[4]), attach_Y=int(arr[5]),
        )

    # ── 判断 ──

    def is_pass(self) -> bool:
        return self.core_rank == -1

    # ── 计数 ──

    def total(self) -> int:
        return (self.core_count + self.attach_2
                + self.attach_BJ + self.attach_RJ + self.attach_Y)

    def wang_list_desc(self) -> list:
        """挂的王/鹰按级别（rank index）降序列出。Y=15, RJ=14, BJ=13。"""
        return ([RANK_INDEX['Y']] * self.attach_Y
                + [RANK_INDEX['RJ']] * self.attach_RJ
                + [RANK_INDEX['BJ']] * self.attach_BJ)

    def attach_wangs_total(self) -> int:
        return self.attach_BJ + self.attach_RJ + self.attach_Y

    def is_gouji(self) -> bool:
        """是否够级牌：含挂画 OR 满足够级数量门槛。"""
        if self.is_pass():
            return False
        if self.attach_wangs_total() > 0:
            return True
        eff = self.core_count + self.attach_2
        if self.core_rank == RANK_INDEX['T'] and eff >= 5: return True
        if self.core_rank == RANK_INDEX['J'] and eff >= 4: return True
        if self.core_rank == RANK_INDEX['Q'] and eff >= 3: return True
        if self.core_rank == RANK_INDEX['K'] and eff >= 2: return True
        if self.core_rank == RANK_INDEX['A'] and eff >= 2: return True
        if self.core_rank == RANK_INDEX['2'] and eff >= 1: return True
        return False

    def is_pure_gouji(self) -> bool:
        """是否纯够级牌：够级牌是否贴2挂花。"""
        if self.is_gouji() and self.attach_2 == 0 and self.attach_wangs_total() == 0:
            return True
        return False


PASS_PLAY = Play(core_rank=-1, core_count=0, attach_2=0,
                 attach_BJ=0, attach_RJ=0, attach_Y=0)


# ── 王杀规则辅助 ──────────────────────────────────────────

def _can_wangs_cover(new_wangs: list, cur_wangs: list) -> set:
    """回溯搜索 new 中的王覆盖 cur 中的所有王，返回可能的剩余王数集合。

    new_wangs / cur_wangs: 降序 rank_index 列表（仅王 BJ/RJ/Y）。
    返回: 匹配后 new 中可能剩余的王数集合，空集=无法覆盖。

    规则：正常(高杀低)、平级(同级1v1)、二杀一、三杀一(BJ→RJ, RJ→Y)。
    """
    if not cur_wangs:
        return {len(new_wangs)}
    if not new_wangs or len(new_wangs) < len(cur_wangs):
        return set()

    cur = cur_wangs[0]
    rest_cur = cur_wangs[1:]
    results = set()

    # 1) 正常 1v1：更高级王
    for i, w in enumerate(new_wangs):
        if w > cur:
            remaining = list(new_wangs)
            remaining.pop(i)
            results.update(_can_wangs_cover(remaining, rest_cur))

    # 2) 二杀一：2 张同 rank 王
    same_idx = [i for i, w in enumerate(new_wangs) if w == cur]
    for combo in combinations(same_idx, 2):
        remaining = [new_wangs[j] for j in range(len(new_wangs))
                     if j not in combo]
        results.update(_can_wangs_cover(remaining, rest_cur))

    # 3) 三杀一：3 张低一级王 → 1 张高一级王
    lower = cur - 1
    if cur >= RANK_INDEX['RJ'] and lower >= RANK_INDEX['BJ']:
        lower_idx = [i for i, w in enumerate(new_wangs) if w == lower]
        for combo in combinations(lower_idx, 3):
            remaining = [new_wangs[j] for j in range(len(new_wangs))
                         if j not in combo]
            results.update(_can_wangs_cover(remaining, rest_cur))

    return results


class GoujiJudger:
    """够级牌型解析与比牌的静态方法集合。"""

    @staticmethod
    def parse_play(ranks: list) -> Play:
        """将 rank 字符串列表解析成 Play。

        规则顺序：
        1. 空列表：过牌
        2. 只有王/鹰：core_rank 取其中最小的王/鹰，王/鹰数量记入 attach
        3. 只有 2 和王/鹰，或者只有 2：core_rank 为 2，2 的数量记入 attach_2
        4. 其他情况：王/鹰 → attach；2 → attach_2；其余必须同 rank → core
        """
        if len(ranks) == 0:
            return PASS_PLAY

        BJs = [r for r in ranks if r == 'BJ']
        RJs = [r for r in ranks if r == 'RJ']
        Ys = [r for r in ranks if r == 'Y']
        twos = [r for r in ranks if r == '2']
        others = [r for r in ranks if r not in {'2', 'BJ', 'RJ', 'Y'}]

        has_wang = bool(BJs or RJs or Ys)

        # 规则 2：只有王/鹰，包括纯同种王/鹰、混合王/鹰
        if not others and not twos and has_wang:
            wang_ranks = []
            if BJs:
                wang_ranks.append(RANK_INDEX['BJ'])
            if RJs:
                wang_ranks.append(RANK_INDEX['RJ'])
            if Ys:
                wang_ranks.append(RANK_INDEX['Y'])

            return Play(
                core_rank=min(wang_ranks),
                core_count=0,
                attach_2=0,
                attach_BJ=len(BJs),
                attach_RJ=len(RJs),
                attach_Y=len(Ys),
            )

        # 规则 3：只有 2，或者只有 2 + 王/鹰
        if not others and twos:
            return Play(
                core_rank=RANK_INDEX['2'],
                core_count=len(twos),
                attach_2=0,
                attach_BJ=len(BJs),
                attach_RJ=len(RJs),
                attach_Y=len(Ys),
            )

        # 规则 4：其他情况
        others_ranks = set(others)
        if len(others_ranks) > 1:
            raise ValueError(f'core 含多种点数: {others}')

        core_rank_str = next(iter(others_ranks))

        return Play(
            core_rank=RANK_INDEX[core_rank_str],
            core_count=len(others),
            attach_2=len(twos),
            attach_BJ=len(BJs),
            attach_RJ=len(RJs),
            attach_Y=len(Ys),
        )

    @staticmethod
    def is_valid_play(ranks: list, hand: np.ndarray) -> bool:
        """合法性检查：手牌包含 + 解析成功 + 至少 1 张。"""
        if not ranks:
            return False
        # hand 是 16-dim 计数向量，检查每张 rank 是否足够
        from collections import Counter
        need = Counter(ranks)
        for r, cnt in need.items():
            if hand[RANK_INDEX[r]] < cnt:
                return False
        try:
            GoujiJudger.parse_play(ranks)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_play_with_constraints(ranks: list, hand: np.ndarray) -> bool:
        """在 is_valid_play 之上加入 3/4 约束。"""
        if not GoujiJudger.is_valid_play(ranks, hand):
            return False
        play = GoujiJudger.parse_play(ranks)

        # 3 约束：必须最后一手单独打出
        if play.core_rank == RANK_INDEX['3']:
            if play.total() != 1:
                return False
            if hand.sum() != 1:
                return False

        # 4 约束：必须一次出完所有 4，不挂
        if play.core_rank == RANK_INDEX['4']:
            n4_in_hand = int(hand[RANK_INDEX['4']])
            if play.core_count != n4_in_hand:
                return False
            if play.attach_2 > 0:
                return False
            if play.attach_wangs_total() > 0:
                return False

        return True

    @staticmethod
    def can_beat(new_cards, current_play: Play) -> bool:
        """new_cards（Play 或 rank 列表）能否压过 current_play。

        规则：
        - 核心 rank 必须严格更大
        - 非王牌（core + attach_2）张数必须一致
        - 王通过杀王规则覆盖（正常/平级/二杀一/三杀一），允许剩余
        - 王覆盖后剩余的王数 = 新牌总数 - 旧牌总数（恰好压完）
        """
        if isinstance(new_cards, Play):
            new_play = new_cards
        else:
            try:
                new_play = GoujiJudger.parse_play(new_cards)
            except ValueError:
                return False

        if new_play.is_pass():
            return False

        # 核心 rank 严格更大
        if new_play.core_rank <= current_play.core_rank:
            return False

        cur_wangs = sorted(current_play.wang_list_desc(), reverse=True)
        new_wangs = sorted(new_play.wang_list_desc(), reverse=True)

        extras = _can_wangs_cover(new_wangs, cur_wangs)
        if not extras:
            return False

        # 王杀后剩余王 + 新非王牌 == 旧非王牌（恰好压完）
        cur_non_wang = current_play.core_count + current_play.attach_2
        new_non_wang = new_play.core_count + new_play.attach_2
        need_extra = cur_non_wang - new_non_wang
        return need_extra in extras

    @staticmethod
    def judge_game(players, finish_order: list) -> bool:
        """判断游戏是否已经结束。

        结束条件：
        场上剩下没走的人是一队。
        """
        num_players = len(players)
        finished_set = set(finish_order)

        remaining = [
            player_id
            for player_id in range(num_players)
            if player_id not in finished_set
        ]

        if not remaining:
            return True

        remaining_teams = [
            players[player_id].team_id
            for player_id in remaining
        ]

        return len(set(remaining_teams)) == 1


    @staticmethod
    def judge_payoffs(players, finish_order: list) -> list:
        """根据走牌顺序结算每个玩家收益。

        规则：
        第 1 个走：所在队 +4
        第 2 个走：所在队 +2
        第 3 / 4 个走：不加分
        第 5 个走：所在队 -2
        第 6 个走：所在队 -4

        如果场上剩下没走的人是一队，则把剩余名次的扣分直接结算到该队。

        每个玩家最终得分 = 所在队伍总分 / 3。

        特殊规则：
        如果先走的三个人是同一队，则该队每人 +12，另一队每人 -12。
        """
        num_players = len(players)

        if not GoujiJudger.judge_game(players, finish_order):
            return [0.0 for _ in range(num_players)]

        # 特殊规则：先走的三个人是同一队
        if len(finish_order) >= 3:
            first_three_teams = [
                players[player_id].team_id
                for player_id in finish_order[:3]
            ]

            if len(set(first_three_teams)) == 1:
                winning_team = first_three_teams[0]

                return [
                    12.0 if player.team_id == winning_team else -12.0
                    for player in players
                ]

        rank_scores = [4, 2, 0, 0, -2, -4]

        team_scores = {}
        for player in players:
            team_scores.setdefault(player.team_id, 0)

        finished_set = set(finish_order)

        remaining = [
            player_id
            for player_id in range(num_players)
            if player_id not in finished_set
        ]

        # 游戏结束时，remaining 必然是一队。
        # 剩余玩家的具体顺序不重要，因为剩余扣分都结算到同一队。
        final_order = list(finish_order) + remaining

        for rank_index, player_id in enumerate(final_order):
            team_id = players[player_id].team_id
            team_scores[team_id] += rank_scores[rank_index]

        return [
            team_scores[player.team_id] / 3
            for player in players
        ]
    @staticmethod
    def playable_cards_from_hand(hand: np.ndarray, last_play: Optional[Play],
                                  player_id: int = 0,
                                  last_player_id: Optional[int] = None,
                                  player_status: Optional[list] = None) -> set:
        """枚举所有合法出牌字符串集合（含 'pass'/'yield' 当合适）。

        hand: 16-dim int32 计数向量

        last_play=None：本轮第一手，枚举所有 parse_play 成功的组合（应用 3/4 约束）。
        last_play 非空：只保留能 can_beat 的组合 + 'pass'。
        yield：对家出牌且其后两人均过牌时可选。
        """
        playable = set()

        # ── 出牌枚举 ──
        # 按 rank 构建候选池：每个 rank 字符串重复手牌中的次数
        non_attach_ranks = [r for r in RANK_STR
                            if r not in ATTACH_RANKS and hand[RANK_INDEX[r]] > 0]

        n2 = int(hand[RANK_INDEX['2']])
        nBJ = int(hand[RANK_INDEX['BJ']])
        nRJ = int(hand[RANK_INDEX['RJ']])
        nY = int(hand[RANK_INDEX['Y']])

        candidates = []

        def gen_with_attach(core_ranks_list):
            """对 core rank 列表生成所有贴/挂组合。"""
            results = []
            for a2 in range(0, n2 + 1):
                for aBJ in range(0, nBJ + 1):
                    for aRJ in range(0, nRJ + 1):
                        for aY in range(0, nY + 1):
                            full = (list(core_ranks_list)
                                    + ['2'] * a2
                                    + ['BJ'] * aBJ
                                    + ['RJ'] * aRJ
                                    + ['Y'] * aY)
                            if not full:
                                continue
                            results.append(full)
            return results

        # (a) 非 attach rank 的 core
        for rank in non_attach_ranks:
            count = int(hand[RANK_INDEX[rank]])
            for k in range(1, count + 1):
                core_ranks = [rank] * k
                candidates.extend(gen_with_attach(core_ranks))

        # (b) 全 2 的 core（不带 attach_2，但可挂王/鹰）
        if n2 > 0:
            for k in range(1, n2 + 1):
                core_ranks = ['2'] * k
                for aBJ in range(0, nBJ + 1):
                    for aRJ in range(0, nRJ + 1):
                        for aY in range(0, nY + 1):
                            full = (core_ranks
                                    + ['BJ'] * aBJ
                                    + ['RJ'] * aRJ
                                    + ['Y'] * aY)
                            candidates.append(full)

        # (c) 纯单类王/鹰（三大王、二鹰 等）
        for r, cnt in [('BJ', nBJ), ('RJ', nRJ), ('Y', nY)]:
            for k in range(1, cnt + 1):
                candidates.append([r] * k)

        # 过滤：合法 + 满足 3/4 约束 + 满足跟牌
        for cand in candidates:
            if not GoujiJudger.is_valid_play_with_constraints(cand, hand):
                continue
            if last_play is not None and not last_play.is_pass():
                if not GoujiJudger.can_beat(cand, last_play):
                    continue
            # cand 是 rank 字符串列表，直接排序后用 '|' 连接
            playable.add('|'.join(sorted(cand, key=lambda r: RANK_INDEX[r])))

        # ── pass / yield ──
        if last_play is not None and not last_play.is_pass():
            playable.add('pass')
            # yield: 对家出牌且对家后两人均过牌
            if (last_player_id is not None
                    and last_player_id != player_id
                    and is_duimen(last_player_id, player_id)
                    and player_status is not None
                    and player_status[(last_player_id - 1) % 6] == 3   # PASSED
                    and player_status[(last_player_id - 2) % 6] == 3):  # PASSED
                playable.add('yield')

        return playable
