"""够级轮次状态机。"""
from enum import IntEnum
from typing import Optional

from .judger import Play
from .utils import duimen_of


class PlayerRoundStatus(IntEnum):
    LEADING = 0  # 本轮发牌权拥有者，待出牌
    ACTIVE = 1   # 待行动
    PLAYED = 2   # 已出过牌
    PASSED = 3   # 已过牌
    YIELDED = 4  # 已让牌


class GoujiRound:
    """单轮状态机。

    一轮的生命周期：
      - 初始：leader_id 为 LEADING，其余 ACTIVE
      - leader 必须出牌（不可 pass/yield）
      - 后续玩家逆时针决策（出 / 过 / 让）
      - 任何 PLAYED 后，所有 YIELDED 自动 → PASSED
      - 够级例外 A: 某玩家出够级牌 → 其对门 PASSED → ACTIVE
      - 够级例外 B: 当前 greater_player 是 P 的对门，且其他人都 PASSED/YIELDED
                    → P 的 PASSED → ACTIVE
      - 终止：没有 ACTIVE/LEADING/YIELDED 玩家
    """

    NUM_PLAYERS = 6

    def __init__(self, leader_id: int = 0):
        self.last_play: Optional[Play] = None
        self.last_player_id: Optional[int] = None
        self.greater_player_id: Optional[int] = None
        self.current_player_id: int = leader_id
        self.player_status: list = [PlayerRoundStatus.ACTIVE] * self.NUM_PLAYERS
        self.player_status[leader_id] = PlayerRoundStatus.LEADING
        # 已通过例外B重启过的玩家（每人本轮最多一次，防无限循环）
        self._exception_b_used: set = set()

    def proceed(self, action: str, parsed_play: Optional[Play]) -> bool:
        """处理一次动作。返回是否本轮结束。"""
        pid = self.current_player_id

        if action == 'pass':
            self.player_status[pid] = PlayerRoundStatus.PASSED
        elif action == 'yield':
            self.player_status[pid] = PlayerRoundStatus.YIELDED
        else:
            # 出牌
            assert parsed_play is not None and not parsed_play.is_pass
            self.last_play = parsed_play
            self.last_player_id = pid
            self.greater_player_id = pid
            self.player_status[pid] = PlayerRoundStatus.PLAYED
            # YIELDED → PASSED
            for i in range(self.NUM_PLAYERS):
                if self.player_status[i] == PlayerRoundStatus.YIELDED:
                    self.player_status[i] = PlayerRoundStatus.PASSED
            # 例外A：对门出够级牌 → 重启
            if parsed_play.is_gouji():
                duimen = duimen_of(pid)
                if self.player_status[duimen] == PlayerRoundStatus.PASSED:
                    self.player_status[duimen] = PlayerRoundStatus.ACTIVE

        return self._advance_turn()

    def _advance_turn(self) -> bool:
        """切到下一个待决策的玩家；返回 True 若本轮结束。"""
        # 例外B：对门牌其他人均 PASSED/YIELDED → 重启
        # 每位玩家本轮最多通过例外B重启一次（防无限循环）
        if self.greater_player_id is not None:
            for pid in range(self.NUM_PLAYERS):
                if pid in self._exception_b_used:
                    continue
                if self.player_status[pid] != PlayerRoundStatus.PASSED:
                    continue
                if duimen_of(pid) != self.greater_player_id:
                    continue
                others = [i for i in range(self.NUM_PLAYERS)
                          if i != pid and i != self.greater_player_id]
                if all(self.player_status[i] in
                       (PlayerRoundStatus.PASSED, PlayerRoundStatus.YIELDED)
                       for i in others):
                    self.player_status[pid] = PlayerRoundStatus.ACTIVE
                    self._exception_b_used.add(pid)

        n = self.current_player_id
        # 优先级 1: 沿逆时针找 ACTIVE / LEADING
        for offset in range(1, self.NUM_PLAYERS + 1):
            nxt = (n - offset) % self.NUM_PLAYERS
            if self.player_status[nxt] in (
                PlayerRoundStatus.ACTIVE, PlayerRoundStatus.LEADING
            ):
                self.current_player_id = nxt
                return False

        # 优先级 2: 找 YIELDED
        for offset in range(1, self.NUM_PLAYERS + 1):
            nxt = (n - offset) % self.NUM_PLAYERS
            if self.player_status[nxt] == PlayerRoundStatus.YIELDED:
                self.current_player_id = nxt
                return False

        return True

    def reset_for_next_round(self) -> None:
        """获得牌权的玩家成为新一轮 LEADING。"""
        new_leader = self.greater_player_id
        assert new_leader is not None
        self.last_play = None
        self.last_player_id = None
        self.greater_player_id = None
        self.player_status = [PlayerRoundStatus.ACTIVE] * self.NUM_PLAYERS
        self.player_status[new_leader] = PlayerRoundStatus.LEADING
        self.current_player_id = new_leader
        self._exception_b_used = set()

    def is_leading(self) -> bool:
        """当前玩家是否本轮首发（必须出牌，不能 pass/yield）。"""
        return (self.player_status[self.current_player_id]
                == PlayerRoundStatus.LEADING)
