"""够级买3 / 买4 自动逻辑。"""
from .utils import is_lianbang, buyer_priority_sellers


COST_RANKS_ORDER = ['2', 'BJ', 'RJ']   # 非联邦付出代价的优先序


def execute_buy(rank: str, players) -> list:
    """让每个玩家至少有 1 张该 rank（如可能）。

    优先级：对门 → 联邦 → 上下家。
    联邦免费；非联邦按 2/BJ/RJ 顺序付一张代价；都没则免费。

    返回交易记录列表 [(buyer_id, seller_id, rank, cost_rank_or_None)]。
    """
    counts = [sum(1 for c in p.hand if c.rank == rank) for p in players]
    available = {i: counts[i] - 1 for i in range(6) if counts[i] >= 2}
    buyers = [i for i in range(6) if counts[i] == 0]

    trades = []
    for buyer in buyers:
        for cand in buyer_priority_sellers(buyer):
            if available.get(cand, 0) > 0:
                cost = _trade(buyer, cand, rank, players)
                trades.append((buyer, cand, rank, cost))
                available[cand] -= 1
                if available[cand] == 0:
                    del available[cand]
                break
    return trades


def _trade(buyer_id: int, seller_id: int, rank: str, players) -> str:
    """执行一次交易；返回付出的代价 rank（联邦/无代价时为 None）。"""
    buyer, seller = players[buyer_id], players[seller_id]

    target = next(c for c in seller.hand if c.rank == rank)
    seller.hand.remove(target)
    buyer.hand.append(target)

    if is_lianbang(buyer_id, seller_id):
        return None

    for cost_rank in COST_RANKS_ORDER:
        cost = next((c for c in buyer.hand if c.rank == cost_rank), None)
        if cost is not None:
            buyer.hand.remove(cost)
            seller.hand.append(cost)
            return cost_rank
    return None
