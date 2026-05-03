"""够级（Gouji）环境，接入 RLCard Env 框架。"""
from collections import OrderedDict

import numpy as np

from rlcard.envs import Env
from rlcard.games.gouji.game import GoujiGame
from rlcard.games.gouji.utils import NUM_RANKS, RANK_MAX_COUNT, RANK_STR

OBS_DIM = 135   # 16+80+6+16+5+6+6


class GoujiEnv(Env):
    """
    状态向量（135维）：
      [0:16]     自己手牌 rank 计数（归一化）
      [16:96]    其他5位已出牌 × 16
      [96:102]   各玩家剩余牌数 / 52
      [102:118]  当前轮最后出牌 rank 计数
      [118:123]  last_play 元数据（core_rank/15, core_count/52,
                   attach_2/52, attach_wangs/18, is_gouji）
      [123:129]  最后出牌者位置 one-hot（6维）
      [129:135]  6玩家本轮状态 / 4（直接归一化）
    """

    def __init__(self, config):
        self.name = 'gouji'
        self.game = GoujiGame()
        super().__init__(config=config)
        self.state_shape = [[OBS_DIM] for _ in range(self.num_players)]
        self.action_shape = [None for _ in range(self.num_players)]

    def _extract_state(self, state: dict) -> dict:
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        # 手牌归一化：16维 int32 → float32 / RANK_MAX_COUNT
        hand = state['current_hand_arr']
        for i in range(NUM_RANKS):
            obs[i] = float(hand[i]) / RANK_MAX_COUNT[RANK_STR[i]]

        for i, arr in enumerate(state['others_played_arr']):
            obs[16 + i*16: 16 + (i+1)*16] = arr

        obs[96:102] = np.array(state['num_cards_left'], dtype=np.float32) / 52.0

        obs[102:118] = state['last_play_array']

        lp = state['last_play_meta']
        obs[118] = lp['core_rank'] / 15.0 if lp['core_rank'] >= 0 else -1.0
        obs[119] = lp['core_count'] / 52.0
        obs[120] = lp['attach_2'] / 52.0
        obs[121] = lp['attach_wangs_total'] / 18.0
        obs[122] = float(lp['is_gouji'])

        last_pid = state['last_player_id']
        if last_pid is not None:
            obs[123 + last_pid] = 1.0

        for i, s in enumerate(state['player_round_status']):
            obs[129 + i] = s / 4.0

        # legal_actions: OrderedDict {action_str: None}
        legal_actions = OrderedDict(
            (a, None) for a in sorted(state['actions']))

        return {
            'obs': obs,
            'legal_actions': legal_actions,
            'raw_obs': state,
            'raw_legal_actions': list(state['actions']),
            'action_record': self.action_recorder,
        }

    def _decode_action(self, action):
        """动作已经是字符串，直接返回。"""
        return action

    def get_payoffs(self):
        return self.game.get_payoffs()

    def _get_legal_actions(self):
        """供 Env 内部调用（此处不使用，由 get_state 返回）。"""
        state = self.game.get_state(self.game.get_player_id())
        return OrderedDict((a, None) for a in sorted(state['actions']))
