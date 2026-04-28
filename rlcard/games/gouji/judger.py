"""够级牌型解析与比牌核心。"""
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

from .utils import (
    RANK_INDEX, RANK_STR, ATTACH_RANKS, WANG_RANKS,
    is_attach_card, get_rank_index, cards2str, is_duimen,
)


@dataclass
class Play:
    """一次出牌的结构化解析结果。"""
    core_rank: int          # 0-15, -1 = 边界（仅 is_pass 时）
    core_count: int
    attach_2: int
    attach_BJ: int
    attach_RJ: int
    attach_Y: int
    is_pass: bool = False

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
        if self.is_pass:
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
    
    def is_pure_gouji(self)->bool:
        """是否纯够级牌：够级牌是否贴2挂花。"""
        if self.is_gouji() and self.attach_2==0 and self.attach_wangs_total()==0: return True
        return False
    
PASS_PLAY = Play(core_rank=-1, core_count=0, attach_2=0,
                 attach_BJ=0, attach_RJ=0, attach_Y=0, is_pass=True)


class GoujiJudger:
    """够级牌型解析与比牌的静态方法集合。"""

    @staticmethod
    def parse_play(cards: list) -> Play:
        """将 Card 列表解析成 Play。

        规则顺序：
        1. 空列表：过牌
        2. 只有王/鹰：core_rank 取其中最小的王/鹰，王/鹰数量记入 attach
        3. 只有 2 和王/鹰，或者只有 2：core_rank 为 2，2 的数量记入 attach_2
        4. 其他情况：王/鹰 → attach；2 → attach_2；其余必须同 rank → core
        """
        if len(cards) == 0:
            return PASS_PLAY

        BJs = [c for c in cards if c.rank == 'BJ']
        RJs = [c for c in cards if c.rank == 'RJ']
        Ys = [c for c in cards if c.rank == 'Y']
        twos = [c for c in cards if c.rank == '2']
        others = [c for c in cards if c.rank not in {'2', 'BJ', 'RJ', 'Y'}]

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
                core_count=0,
                attach_2=len(twos),
                attach_BJ=len(BJs),
                attach_RJ=len(RJs),
                attach_Y=len(Ys),
            )

        # 规则 4：其他情况
        # 此时必须存在普通牌，且普通牌只能有一种 rank
        others_ranks = set(c.rank for c in others)

        if len(others_ranks) > 1:
            raise ValueError(
                f'core 含多种点数: {[c.rank for c in others]}'
            )

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
    def is_valid_play(cards: list, hand: list) -> bool:
        """合法性检查：手牌包含 + 解析成功 + 至少 1 张。"""
        if not cards:
            return False
        # 多重集包含检查（按 (suit, rank) 唯一性）
        from collections import Counter
        hand_counter = Counter((c.suit, c.rank) for c in hand)
        play_counter = Counter((c.suit, c.rank) for c in cards)
        for k, v in play_counter.items():
            if hand_counter.get(k, 0) < v:
                return False
        try:
            GoujiJudger.parse_play(cards)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_play_with_constraints(cards: list, hand: list) -> bool:
        """在 is_valid_play 之上加入 3/4 约束。"""
        if not GoujiJudger.is_valid_play(cards, hand):
            return False
        play = GoujiJudger.parse_play(cards)

        # 3 约束：必须最后一手单独打出
        if play.core_rank == RANK_INDEX['3']:
            if play.total() != 1:
                return False
            if len(hand) != 1:
                return False
        # 任何含 3 的牌（实际上 3 不会作为 attach，所以只可能是 core）
        # core_rank=3 已被上面处理，无需额外检查

        # 4 约束：必须一次出完所有 4，不挂
        if play.core_rank == RANK_INDEX['4']:
            n4_in_hand = sum(1 for c in hand if c.rank == '4')
            if play.core_count != n4_in_hand:
                return False
            if play.attach_2 > 0:
                return False
            if play.attach_wangs_total() > 0:
                return False

        return True

    @staticmethod
    def can_beat(new_cards: list, current_play: Play) -> bool:
        """new_cards 能否压过 current_play。"""
        try:
            new_play = GoujiJudger.parse_play(new_cards)
        except ValueError:
            return False
        if new_play.is_pass:
            return False

        if new_play.total() != current_play.total():
            return False

        # 鹰挂不可被压
        if current_play.attach_Y > 0:
            return False

        # 王覆盖：逐位严格管
        cur_wangs = sorted(current_play.wang_list_desc(), reverse=True)
        new_wangs = sorted(new_play.wang_list_desc(), reverse=True)
        if len(cur_wangs) > len(new_wangs):
            return False
        for i in range(len(cur_wangs)):
            if new_wangs[i] <= cur_wangs[i]:
                return False

        # core_rank 严格更大
        return new_play.core_rank > current_play.core_rank

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
    def playable_cards_from_hand(hand: list, last_play: Optional[Play],
                                  player_id: int = 0,
                                  last_player_id: Optional[int] = None,
                                  player_status: Optional[list] = None) -> set:
        """枚举所有合法出牌字符串集合（含 'pass'/'yield' 当合适）。

        last_play=None：本轮第一手，枚举所有 parse_play 成功的组合（应用 3/4 约束）。
        last_play 非空：只保留能 can_beat 的组合 + 'pass'。
        yield：对家出牌且其后两人均过牌时可选。
        """
        playable = set()

        # ── 出牌枚举 ──
        # 按 rank 分组手牌
        rank_groups = {}
        for c in hand:
            rank_groups.setdefault(c.rank, []).append(c)

        attach_2_pool = rank_groups.get('2', [])
        BJ_pool = rank_groups.get('BJ', [])
        RJ_pool = rank_groups.get('RJ', [])
        Y_pool = rank_groups.get('Y', [])

        # 非 attach 的 rank 组
        non_attach_groups = {r: cs for r, cs in rank_groups.items()
                             if r not in ATTACH_RANKS}

        candidates = []

        def gen_with_attach(core_cards):
            """对 core_cards 生成所有贴/挂组合。"""
            results = []
            for n2 in range(0, len(attach_2_pool) + 1):
                for nBJ in range(0, len(BJ_pool) + 1):
                    for nRJ in range(0, len(RJ_pool) + 1):
                        for nY in range(0, len(Y_pool) + 1):
                            full = (list(core_cards)
                                    + attach_2_pool[:n2]
                                    + BJ_pool[:nBJ]
                                    + RJ_pool[:nRJ]
                                    + Y_pool[:nY])
                            if not full:
                                continue
                            results.append(full)
            return results

        # (a) 非 attach rank 的 core
        for rank, cs in non_attach_groups.items():
            for k in range(1, len(cs) + 1):
                core_cards = cs[:k]
                candidates.extend(gen_with_attach(core_cards))

        # (b) 全 2 的 core（不带 attach_2，但可挂王/鹰）
        if attach_2_pool:
            for k in range(1, len(attach_2_pool) + 1):
                core_cards = attach_2_pool[:k]
                # 在这种情况下 attach_2_pool 已被全部用作 core，不再贴 2
                for nBJ in range(0, len(BJ_pool) + 1):
                    for nRJ in range(0, len(RJ_pool) + 1):
                        for nY in range(0, len(Y_pool) + 1):
                            full = (list(core_cards)
                                    + BJ_pool[:nBJ]
                                    + RJ_pool[:nRJ]
                                    + Y_pool[:nY])
                            candidates.append(full)

        # (c) 纯单类王/鹰（三大王、二鹰 等）
        for pool in (BJ_pool, RJ_pool, Y_pool):
            for k in range(1, len(pool) + 1):
                candidates.append(pool[:k])

        # 过滤：合法 + 满足 3/4 约束 + 满足跟牌
        for cand in candidates:
            if not GoujiJudger.is_valid_play_with_constraints(cand, hand):
                continue
            if last_play is not None and not last_play.is_pass:
                if not GoujiJudger.can_beat(cand, last_play):
                    continue
            playable.add(cards2str(cand))

        # ── pass / yield ──
        if last_play is not None and not last_play.is_pass:
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
