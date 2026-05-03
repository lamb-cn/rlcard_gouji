"""够级发牌：6副+鹰，每人52张，含买3/买4。"""
from .utils import (
    HAND_SIZE, RANK_INDEX, is_lianbang, buyer_priority_sellers,
)

NORMAL_RANKS = ['3', '4', '5', '6', '7', '8', '9',
                'T', 'J', 'Q', 'K', 'A', '2']

COST_RANKS_ORDER = ['2', 'BJ', 'RJ']

# 买牌优先级轮次：第0轮全员对家，第1-2轮全员联邦，第3-4轮全员上下家
BUY_PRIORITY_ROUNDS = [0, 1, 2, 3, 4]


class GoujiDealer:

    def __init__(self, np_random):
        self.np_random = np_random
        self.deck = self._build_deck()

    def _build_deck(self) -> list:
        """构建牌组：rank 字符串列表。"""
        cards = []
        for _ in range(6):
            for rank in NORMAL_RANKS:
                cards.extend([rank] * 4)
            cards.append('BJ')
            cards.append('RJ')

        # 移除多余的 3：原本 24 张，只留 6 张
        threes = [c for c in cards if c == '3']
        non_threes = [c for c in cards if c != '3']
        keep_indices = self.np_random.choice(len(threes), size=6, replace=False)
        keep_threes = [threes[i] for i in keep_indices]
        cards = non_threes + keep_threes

        cards += ['Y'] * 6
        return cards

    def deal(self, players) -> None:
        """向每个玩家发 52 张，然后买3/4。"""
        self.np_random.shuffle(self.deck)
        for i, p in enumerate(players):
            chunk = self.deck[i * HAND_SIZE: (i + 1) * HAND_SIZE]
            for r in chunk:
                p.hand[RANK_INDEX[r]] += 1
        self._execute_buy('3', players)
        self._execute_buy('4', players)

    # ── 买牌 ─────────────────────────────────────────────────

    def _execute_buy(self, rank: str, players) -> list:
        """让每个玩家至少有 1 张该 rank。

        优先级轮次：先全员对家 → 再全员联邦 → 再全员上下家。
        联邦免费；非联邦按 2/BJ/RJ 顺序付一张代价；都没则免费。
        """
        idx = RANK_INDEX[rank]
        counts = [int(p.hand[idx]) for p in players]
        available = {i: counts[i] - 1 for i in range(6) if counts[i] >= 2}
        buyers = [i for i in range(6) if counts[i] == 0]

        trades = []
        for priority_idx in BUY_PRIORITY_ROUNDS:
            resolved = []
            for buyer in buyers:
                sellers = buyer_priority_sellers(buyer)
                cand = sellers[priority_idx]
                if available.get(cand, 0) > 0:
                    cost = self._trade(buyer, cand, idx, players)
                    trades.append((buyer, cand, rank, cost))
                    available[cand] -= 1
                    if available[cand] == 0:
                        del available[cand]
                    resolved.append(buyer)
            for b in resolved:
                buyers.remove(b)
            if not buyers:
                break
        return trades

    def _trade(self, buyer_id: int, seller_id: int, idx: int, players):
        """执行一次交易；返回付出的代价 rank（联邦/无代价时为 None）。"""
        buyer, seller = players[buyer_id], players[seller_id]

        seller.hand[idx] -= 1
        buyer.hand[idx] += 1

        if is_lianbang(buyer_id, seller_id):
            return None

        for cost_rank in COST_RANKS_ORDER:
            cost_idx = RANK_INDEX[cost_rank]
            if buyer.hand[cost_idx] > 0:
                buyer.hand[cost_idx] -= 1
                seller.hand[cost_idx] += 1
                return cost_rank
        return None
