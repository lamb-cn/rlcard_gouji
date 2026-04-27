"""够级游戏主逻辑。"""
from collections import Counter

import numpy as np

from .dealer import GoujiDealer
from .player import GoujiPlayer
from .judger import GoujiJudger
from .round import GoujiRound, PlayerRoundStatus
from .buy_phase import execute_buy
from .utils import (
    NUM_PLAYERS, HAND_SIZE, RANK_INDEX,
    hand_to_normalized_array, cards2str, team_id,
)


class GoujiGame:
    """够级游戏引擎（与 RLCard Env 框架对接）。"""

    def __init__(self, allow_step_back=False):
        self.allow_step_back = allow_step_back
        self.np_random = np.random.RandomState()

        # 供 Env.__init__ 读取
        self.num_players = NUM_PLAYERS
        self.num_actions = 1   # 动态动作空间，仅占位

    # ── RLCard 必要接口 ──────────────────────────────────────────

    def get_num_players(self):
        return NUM_PLAYERS

    def get_num_actions(self):
        return self.num_actions

    def get_player_id(self):
        return self.round.current_player_id

    def is_over(self):
        return self.winner_team >= 0

    # ── 初始化 ────────────────────────────────────────────────────

    def init_game(self):
        """发牌 → 买3 → 买4 → 初始化轮次。"""
        self.winner_team = -1

        self.players = [GoujiPlayer(i) for i in range(NUM_PLAYERS)]
        self.dealer = GoujiDealer(self.np_random)
        self.dealer.deal(self.players)

        execute_buy('3', self.players)
        execute_buy('4', self.players)

        self.judger = GoujiJudger()

        # 玩家 0 先发（Phase 2 会实现上班/抢班/大落）
        self.round = GoujiRound(leader_id=0)

        # 每位玩家的累计已出牌（按 rank 计数，用于 obs）
        self._played_arrays = [
            np.zeros(16, dtype=np.float32) for _ in range(NUM_PLAYERS)
        ]

        pid = self.round.current_player_id
        state = self.get_state(pid)
        return state, pid

    # ── 单步 ────────────────────────────────────────────────────

    def step(self, action: str):
        """执行一个动作（字符串）并返回 (state, next_player_id)。"""
        pid = self.round.current_player_id
        player = self.players[pid]

        if action in ('pass', 'yield'):
            parsed_play = None
        else:
            # 从手牌中找出对应的 Card 对象
            cards = self._pick_cards_for_action(player.hand, action)
            parsed_play = GoujiJudger.parse_play(cards)
            # 移除手牌、记录已出
            player.remove_cards(cards)
            player.played_history.extend(cards)
            # 更新已出数组（用 rank 计数，归一化）
            for c in cards:
                ri = RANK_INDEX[c.rank]
                from .utils import RANK_MAX_COUNT, RANK_STR
                self._played_arrays[pid][ri] += (
                    1.0 / RANK_MAX_COUNT[RANK_STR[ri]])

        round_over = self.round.proceed(action, parsed_play)

        # 检查游戏结束（手牌清空）
        winner = GoujiJudger.judge_game(self.players)
        if winner >= 0:
            self.winner_team = winner

        if round_over and not self.is_over():
            self.round.reset_for_next_round()

        next_pid = self.round.current_player_id
        state = self.get_state(next_pid)
        return state, next_pid

    # ── 状态 ─────────────────────────────────────────────────────

    def get_state(self, player_id: int) -> dict:
        """构造 raw_state（供 GoujiEnv._extract_state 消费）。"""
        p = self.players[player_id]

        # 其他5位玩家已出牌（按相对位置：+1, +2, ..., +5）
        others_played = [
            self._played_arrays[(player_id + i) % NUM_PLAYERS]
            for i in range(1, NUM_PLAYERS)
        ]

        last_play = self.round.last_play
        if last_play is None or last_play.is_pass:
            lp_meta = {
                'core_rank': -1, 'core_count': 0,
                'attach_2': 0, 'attach_wangs_total': 0, 'is_gouji': False,
            }
            lp_arr = np.zeros(16, dtype=np.float32)
        else:
            from .utils import RANK_MAX_COUNT, RANK_STR
            lp_arr = np.zeros(16, dtype=np.float32)
            lp_arr[last_play.core_rank] += (
                last_play.core_count
                / RANK_MAX_COUNT[RANK_STR[last_play.core_rank]]
            ) if last_play.core_rank >= 0 else 0
            lp_meta = {
                'core_rank': last_play.core_rank,
                'core_count': last_play.core_count,
                'attach_2': last_play.attach_2,
                'attach_wangs_total': last_play.attach_wangs_total(),
                'is_gouji': last_play.is_gouji(),
            }

        # 合法动作
        actions = GoujiJudger.playable_cards_from_hand(
            p.hand,
            last_play=(last_play if (last_play and not last_play.is_pass) else None),
            player_id=player_id,
            last_player_id=self.round.last_player_id,
        )
        # leader 不能 pass/yield
        if self.round.is_leading():
            actions.discard('pass')
            actions.discard('yield')
        # 保证至少有一个动作（极端情况下强制 pass）
        if not actions:
            actions = {'pass'}

        return {
            'current_hand_arr': hand_to_normalized_array(p.hand),
            'others_played_arr': others_played,
            'num_cards_left': [len(self.players[i].hand) for i in range(NUM_PLAYERS)],
            'last_play_array': lp_arr,
            'last_play_meta': lp_meta,
            'last_player_id': self.round.last_player_id,
            'player_round_status': [int(s) for s in self.round.player_status],
            'actions': actions,
            'self': player_id,
            'team_id': team_id(player_id),
        }

    def get_payoffs(self):
        return GoujiJudger.judge_payoffs(self.winner_team, NUM_PLAYERS)

    # ── 工具 ─────────────────────────────────────────────────────

    @staticmethod
    def _pick_cards_for_action(hand: list, action_str: str) -> list:
        """从手牌中按 rank 选出对应的 Card 列表。

        action_str 格式为 '7|7|BJ'（cards2str 的逆）。
        按 rank 从手牌中依次取第一张匹配的 Card。
        """
        ranks = action_str.split('|')
        remaining = list(hand)
        picked = []
        rank_need = Counter(ranks)
        for rank, count in rank_need.items():
            got = 0
            for c in remaining[:]:
                if c.rank == rank and got < count:
                    picked.append(c)
                    remaining.remove(c)
                    got += 1
            if got < count:
                raise ValueError(
                    f'手牌不足: 需要 {count} 张 {rank}，手牌只有 {got} 张')
        return picked
