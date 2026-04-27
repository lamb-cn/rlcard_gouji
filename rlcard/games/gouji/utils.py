"""够级游戏工具：牌的编码、常量、座位关系。"""
import numpy as np


RANK_STR = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A',
            '2', 'BJ', 'RJ', 'Y']
RANK_INDEX = {r: i for i, r in enumerate(RANK_STR)}

SUIT_STR = ['S', 'H', 'D', 'C']

ATTACH_RANKS = {'2', 'BJ', 'RJ', 'Y'}
WANG_RANKS = {'BJ', 'RJ', 'Y'}

NUM_RANKS = 16
NUM_PLAYERS = 6
HAND_SIZE = 52
TOTAL_CARDS = 312

RANK_MAX_COUNT = {
    '3': 6,
    '4': 24, '5': 24, '6': 24, '7': 24, '8': 24, '9': 24,
    'T': 24, 'J': 24, 'Q': 24, 'K': 24, 'A': 24, '2': 24,
    'BJ': 6, 'RJ': 6, 'Y': 6,
}


def get_rank_index(card) -> int:
    return RANK_INDEX[card.rank]


def is_attach_card(card) -> bool:
    return card.rank in ATTACH_RANKS


def is_wang(card) -> bool:
    return card.rank in WANG_RANKS


def hand_to_rank_array(hand: list) -> np.ndarray:
    """手牌 → 16维 rank 计数向量（不归一化）。"""
    arr = np.zeros(NUM_RANKS, dtype=np.int32)
    for card in hand:
        arr[RANK_INDEX[card.rank]] += 1
    return arr


def hand_to_normalized_array(hand: list) -> np.ndarray:
    """手牌 → 16维 rank 计数向量（除以该 rank 的最大可能数）。"""
    arr = hand_to_rank_array(hand).astype(np.float32)
    for i, rank in enumerate(RANK_STR):
        arr[i] /= RANK_MAX_COUNT[rank]
    return arr


def cards2str(cards: list) -> str:
    """Card 列表 → 唯一字符串表示，按 rank 升序排列，'|' 分隔。"""
    sorted_cards = sorted(cards, key=get_rank_index)
    return '|'.join(c.rank for c in sorted_cards)


def str2ranks(action_str: str) -> list:
    """动作字符串 → rank 列表，例 '7|7|7' → ['7','7','7']。"""
    if action_str in ('pass', 'yield', ''):
        return []
    return action_str.split('|')


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
    """卖家优先级：对门 → 联邦 → 上下家。"""
    return [
        (buyer + 3) % 6,                    # 对门
        (buyer + 2) % 6, (buyer + 4) % 6,   # 联邦
        (buyer + 1) % 6, (buyer - 1) % 6,   # 上下家
    ]
