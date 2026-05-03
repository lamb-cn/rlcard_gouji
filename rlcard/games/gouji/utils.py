"""够级游戏工具：牌的编码、常量、座位关系。"""
from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .judger import Play


RANK_STR = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A',
            '2', 'BJ', 'RJ', 'Y']
RANK_INDEX = {r: i for i, r in enumerate(RANK_STR)}

ATTACH_RANKS = {'2', 'BJ', 'RJ', 'Y'}
WANG_RANKS = {'BJ', 'RJ', 'Y'}

NUM_RANKS = 16
NUM_PLAYERS = 6
HAND_SIZE = 52

RANK_MAX_COUNT = {
    '3': 6,
    '4': 24, '5': 24, '6': 24, '7': 24, '8': 24, '9': 24,
    'T': 24, 'J': 24, 'Q': 24, 'K': 24, 'A': 24, '2': 24,
    'BJ': 6, 'RJ': 6, 'Y': 6,
}


def hand_to_normalized_array(hand: np.ndarray) -> np.ndarray:
    """16维计数向量 → 归一化（除以该 rank 的最大可能数）。"""
    arr = hand.astype(np.float32)
    for i, rank in enumerate(RANK_STR):
        arr[i] /= RANK_MAX_COUNT[rank]
    return arr


def ranks_to_str(ranks: list) -> str:
    """rank 字符串列表 → 排序后的 '|' 分隔字符串。"""
    return '|'.join(sorted(ranks, key=lambda r: RANK_INDEX[r]))


def str2ranks(action_str: str) -> list:
    """动作字符串 → rank 列表，例 '7|7|BJ' → ['7','7','BJ']。"""
    if action_str in ('pass', 'yield', ''):
        return []
    return action_str.split('|')


# ── str ↔ Play 转换 ──

def str_to_play(action_str: str) -> 'Play':
    """'7|7|BJ' → Play; 'pass'/'yield' → PASS_PLAY"""
    from .judger import GoujiJudger, PASS_PLAY
    if action_str in ('pass', 'yield', ''):
        return PASS_PLAY
    ranks = action_str.split('|')
    return GoujiJudger.parse_play(ranks)


def play_to_str(play: 'Play') -> str:
    """Play → 排序后的 '|' 分隔字符串"""
    if play.core_rank == -1:
        return 'pass'
    parts = []
    parts.extend([RANK_STR[play.core_rank]] * play.core_count)
    parts.extend(['2'] * play.attach_2)
    parts.extend(['BJ'] * play.attach_BJ)
    parts.extend(['RJ'] * play.attach_RJ)
    parts.extend(['Y'] * play.attach_Y)
    parts.sort(key=lambda r: RANK_INDEX[r])
    return '|'.join(parts)


def play_to_ranks(play: 'Play') -> list:
    """Play → rank 字符串列表"""
    if play.core_rank == -1:
        return []
    parts = []
    parts.extend([RANK_STR[play.core_rank]] * play.core_count)
    parts.extend(['2'] * play.attach_2)
    parts.extend(['BJ'] * play.attach_BJ)
    parts.extend(['RJ'] * play.attach_RJ)
    parts.extend(['Y'] * play.attach_Y)
    return parts


# ───────────── 座位关系（6 人，0,2,4 vs 1,3,5）─────────────

def team_id(player_id: int) -> int:
    """返回玩家所属队伍：0 或 1。"""
    return player_id % 2


def is_lianbang(p1: int, p2: int) -> bool:
    """是否同队（联邦）：p1≠p2 且同队伍。"""
    return p1 != p2 and team_id(p1) == team_id(p2)


def is_duimen(p1: int, p2: int) -> bool:
    """p2 是否是 p1 的对门：(p1+3) mod 6 == p2。"""
    return (p1 + 3) % 6 == p2


def duimen_of(player_id: int) -> int:
    return (player_id + 3) % 6


def buyer_priority_sellers(buyer: int) -> list:
    """卖家优先级五维向量：[对家, 联邦1, 联邦2, 上家, 下家]."""
    return [
        (buyer + 3) % 6,                    # 0: 对门
        (buyer + 2) % 6, (buyer + 4) % 6,   # 1,2: 联邦
        (buyer + 1) % 6, (buyer - 1) % 6,   # 3,4: 上下家
    ]
