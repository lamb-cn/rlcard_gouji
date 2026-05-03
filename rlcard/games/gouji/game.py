"""够级游戏主逻辑。"""
import numpy as np

from .dealer import GoujiDealer
from .player import GoujiPlayer
from .judger import GoujiJudger
from .round import GoujiRound, PlayerRoundStatus
from .utils import (
    NUM_PLAYERS, RANK_INDEX, RANK_MAX_COUNT, RANK_STR,
    team_id, str_to_play, play_to_ranks,
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

    def get_num_actions(self):
        return self.num_actions

    def get_player_id(self):
        return self.round.current_player_id

    # ── 初始化 ────────────────────────────────────────────────────

    def init_game(self):
        """发牌 → 买3 → 买4 → 初始化轮次。"""
        self.winner_team = -1
        self.finish_order = []

        self.players = [GoujiPlayer(i) for i in range(NUM_PLAYERS)]
        self.dealer = GoujiDealer(self.np_random)
        self.dealer.deal(self.players)

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
            parsed_play = str_to_play(action)
            # 从手牌扣除
            player.remove_cards(parsed_play)
            # 记录已出牌
            ranks = play_to_ranks(parsed_play)
            for r in ranks:
                player.played_history[RANK_INDEX[r]] += 1

            # 如果该玩家出完牌，记录走牌顺序
            if player.hand.sum() == 0 and pid not in self.finish_order:
                self.finish_order.append(pid)

            # 更新已出数组
            for r in ranks:
                ri = RANK_INDEX[r]
                self._played_arrays[pid][ri] += (
                    1.0 / RANK_MAX_COUNT[RANK_STR[ri]])

        round_over = self.round.proceed(action, parsed_play)

        if round_over and not self.is_over():
            self.round.reset_for_next_round()

        # 兼容旧字段
        if self.is_over() and self.winner_team < 0:
            payoffs = self.get_payoffs()
            max_payoff = max(payoffs)
            if max_payoff > 0:
                for i, payoff in enumerate(payoffs):
                    if payoff == max_payoff:
                        self.winner_team = self.players[i].team_id
                        break

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
        if last_play is None or last_play.is_pass():
            lp_meta = {
                'core_rank': -1,
                'core_count': 0,
                'attach_2': 0,
                'attach_wangs_total': 0,
                'is_gouji': False,
            }
            lp_arr = np.zeros(16, dtype=np.float32)
        else:
            lp_arr = np.zeros(16, dtype=np.float32)
            if last_play.core_rank >= 0:
                lp_arr[last_play.core_rank] += (
                    last_play.core_count
                    / RANK_MAX_COUNT[RANK_STR[last_play.core_rank]]
                )

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
            last_play=(last_play if (last_play and not last_play.is_pass()) else None),
            player_id=player_id,
            last_player_id=self.round.last_player_id,
            player_status=self.round.player_status,
        )

        # leader 不能 pass/yield
        if self.round.is_leading():
            actions.discard('pass')
            actions.discard('yield')

        # 保证至少有一个动作（极端情况下强制 pass）
        if not actions:
            actions = {'pass'}

        return {
            'current_hand_arr': p.hand,
            'others_played_arr': others_played,
            'num_cards_left': [
                int(self.players[i].hand.sum())
                for i in range(NUM_PLAYERS)
            ],
            'last_play_array': lp_arr,
            'last_play_meta': lp_meta,
            'last_player_id': self.round.last_player_id,
            'player_round_status': [
                int(s) for s in self.round.player_status
            ],
            'actions': actions,
            'self': player_id,
            'team_id': team_id(player_id),
            'finish_order': list(self.finish_order),
            'finished': [
                i in self.finish_order
                for i in range(NUM_PLAYERS)
            ],
        }

    # ── 终局与收益 ───────────────────────────────────────────────

    def is_over(self):
        return GoujiJudger.judge_game(self.players, self.finish_order)

    def get_payoffs(self):
        return GoujiJudger.judge_payoffs(self.players, self.finish_order)
