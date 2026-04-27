"""够级发牌：6副+鹰，每人52张。"""
from rlcard.games.base import Card

from .utils import SUIT_STR, TOTAL_CARDS, HAND_SIZE


NORMAL_RANKS = ['3', '4', '5', '6', '7', '8', '9',
                'T', 'J', 'Q', 'K', 'A', '2']


class GoujiDealer:

    def __init__(self, np_random):
        self.np_random = np_random
        self.deck = self._build_deck()

    def _build_deck(self) -> list:
        cards = []
        # 6副普通牌：4花色 × 13点数
        for _ in range(6):
            for suit in SUIT_STR:
                for rank in NORMAL_RANKS:
                    cards.append(Card(suit, rank))
            # 每副 2 张王
            cards.append(Card('', 'BJ'))
            cards.append(Card('', 'RJ'))

        # 移除多余的 3：原本 24 张（6副×4花色），只留 6 张
        threes = [c for c in cards if c.rank == '3']
        non_threes = [c for c in cards if c.rank != '3']
        # 用 numpy random 选 6 张 3
        keep_indices = self.np_random.choice(
            len(threes), size=6, replace=False)
        keep_threes = [threes[i] for i in keep_indices]
        cards = non_threes + keep_threes

        # 加 6 张鹰
        cards += [Card('', 'Y') for _ in range(6)]
        assert len(cards) == TOTAL_CARDS, \
            f'expected {TOTAL_CARDS} cards, got {len(cards)}'
        return cards

    def shuffle(self) -> None:
        self.np_random.shuffle(self.deck)

    def deal(self, players) -> None:
        """每人 52 张。3 的均匀分配由 buy_phase 修复。"""
        self.shuffle()
        for i, p in enumerate(players):
            p.hand = list(self.deck[i * HAND_SIZE: (i + 1) * HAND_SIZE])
