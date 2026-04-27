# 够级游戏 - 牌型检验与状态空间实现方案 (v2)

## Context

在 RLCard 框架中添加够级游戏。规则从用户提供的PDF（《够级规则》2024.9.19 张笑鸣）整理。
**本阶段只实现**：牌的编码、牌型检验（Judger）、基础状态空间（envs）。
**后续阶段**：走科/憋三、买3/买4、进贡、革命、烧牌、够级开点、四户乱缠、圈三户等高阶规则。

---

## 牌的核算（重要）

| 项目               | 数量            |
| ---------------- | ------------- |
| 6副标准牌（含王）        | 6×54 = 324    |
| 减去多余的 3 (每人保留1张) | -(24-6) = -18 |
| 加入"鹰"（Y）         | +6            |
| **总牌数**          | **312**       |
| 每人发牌             | 52            |

**唯一牌面种类（按 rank 合并花色后 = 16种）**：

- 13 个普通点数：3, 4, 5, 6, 7, 8, 9, T, J, Q, K, A, 2
- 3 个特殊点数：小王（BJ）、大王（RJ）、鹰（Y）
- **合计 16 种** → 计数向量用 **16维**

> **说明**：内部存储仍然使用 `Card(suit, rank)` 对象（兼容 rlcard 的 base.py），
> 但状态空间 obs 中只按 rank 编码（够级不考虑花色，合并后维度从 55→16，更利于 NN 训练）。
>
> 对于 BJ/RJ/Y 没有花色（统一用 `Card('', 'BJ'/RJ/Y)`），直接按 rank 索引即可。

**牌面大小（固定）**：3 < 4 < 5 < 6 < 7 < 8 < 9 < T < J < Q < K < A < 2 < 小王(BJ) < 大王(RJ) < 鹰(Y)

---

## 规则核心摘要（本阶段相关）

### 1. 牌型与贴/挂的语义（最复杂的部分）

每套出牌可分解为三层：

```
出牌 = [核心牌 core] + [贴钱 attach_2] + [挂画 attach_BJ/RJ/Y]
```

- **核心牌（core）**：相同点数的非2非王牌（rank ≤ A 或 全是2）
- **贴钱（attach_2）**：2 跟随 core 一起出，且 core_rank < 2 时，2 "视为" core_rank
  - 例：`27777` = core(7×4) + attach_2(1) → 视为五个7
- **挂画（attach_BJ / attach_RJ / attach_Y）**：王/鹰随 core 同出，但 **王仍视为王**
  - 例：`小王7777` = core(7×4) + attach_BJ(1) → 小王挂四个7

### 2. 比牌规则（最终版，已与用户确认）

**核心要点**：要压过当前出牌，必须**王覆盖（每个对方的王都有对应级别更高或相等的王管住，且至少cur的王能被覆盖）**且 **core_rank 严格更大**。同时压过纯王/2 的牌时，王覆盖规则单独生效。

**Step 1 — 总张数相同**

```
total = core_count + attach_2 + attach_BJ + attach_RJ + attach_Y
new.total() == cur.total()  必须成立
```

**Step 2 — 鹰挂的牌不可被压**

```
if cur.attach_Y > 0: return False   # 任何对方都压不过
```

**Step 3 — 王挂"逐位严格管"**

把双方所有挂的王/鹰按级别（Y > RJ > BJ）降序排列：

```
cur_wangs = sorted([Y]*cur.attach_Y + [RJ]*cur.attach_RJ + [BJ]*cur.attach_BJ, reverse=True)
new_wangs = sorted([Y]*new.attach_Y + [RJ]*new.attach_RJ + [BJ]*new.attach_BJ, reverse=True)

if len(cur_wangs) > len(new_wangs): return False   # 王数量不够覆盖

for i in range(len(cur_wangs)):
    if new_wangs[i] < cur_wangs[i]: return False   # 第 i 位对方的王没被相应级别覆盖
```

**Step 4 — core_rank 严格更大**

```
return new.core_rank > cur.core_rank
```

**注意**：

- 贴 2（attach_2）不算王，不算 core_rank（"贴2 = 视为 core 的同点数"），只补总张数
- core_rank 相同就不能压（即使 core_count 或 attach_2 不同，如`小王2777` 和 `小王7777` 完全等价）

### 用户确认的关键例子

| 比较（new ← cur）           | total | 鹰挂否 | 王覆盖               | core    | 结论              |
| ----------------------- | ----- | --- | ----------------- | ------- | --------------- |
| `88888` ← `27777`       | 5=5 ✓ | ✓   | 都空 ✓              | 8>7 ✓   | **可压**          |
| `王2888` ← `27777`       | 5=5 ✓ | ✓   | cur=[],new=[BJ] ✓ | 8>7 ✓   | **可压**          |
| `大王挂6666` ← `小王挂7777`   | 5=5 ✓ | ✓   | RJ≥BJ ✓           | 6>7 ✗   | **不可压**         |
| `小王挂7777` ← `大王挂6666`   | 5=5 ✓ | ✓   | BJ<RJ ✗           | —       | **不可压**         |
| `王22` ← `222`           | 3=3 ✓ | ✓   | cur=[],new=[BJ] ✓ | 12>12 ✗ | **不可压**         |
| `三大王` ← `222`           | 3=3 ✓ | ✓   | 都空 ✓              | 14>12 ✓ | **可压**          |
| `三小王` ← `222`           | 3=3 ✓ | ✓   | 都空 ✓              | 13>12 ✓ | **可压**          |
| `两鹰挂999` ← `一大一小挂888`   | 5=5 ✓ | ✓   | [Y,Y]≥[RJ,BJ] ✓   | 9>8 ✓   | **可压**          |
| `一鹰一大挂999` ← `一大一小挂888` | 5=5 ✓ | ✓   | [Y,RJ]≥[RJ,BJ] ✓  | 9>8 ✓   | **可压**          |
| `小王挂8888` ← `小王挂7777`   | 5=5 ✓ | ✓   | [BJ]≥[BJ] ✓       | 8>7 ✓   | **可压**          |
| 任何 ← `鹰挂AAAA`           | —     | ✗   | —                 | —       | **不可压**（鹰挂不可被压） |
| `小王2777` vs `小王7777`    | 5=5 ✓ | ✓   | [BJ]=[BJ]         | 7=7 ✗   | **互不能压（完全等于）**  |

### 3. 够级牌识别（本阶段需要标记，但暂不做权限控制）

任何下列纯牌型或贴2牌型为"够级牌"：

- core_rank=10, effective_count(core+attach_2) ≥ 5
- core_rank=J, effective_count ≥ 4
- core_rank=Q, effective_count ≥ 3
- core_rank=K, effective_count ≥ 2
- core_rank=A, effective_count ≥ 2
- core_rank=2 (即core为2), effective_count ≥ 1

此外，**任何含挂画（BJ/RJ/Y）的牌型** 都是够级牌。

> 注：本阶段只在 Play 上加 `is_gouji` 标记，对门/无头/烧牌等"谁能打够级牌"的逻辑放后续。

---

### 4. 座位关系（已与用户确认）

6人按 0,1,2,3,4,5 **逆时针**落坐：

| 关系 | 玩家 i 对应 |
|------|-------------|
| 队伍 | 0,2,4 → 队0；1,3,5 → 队1 |
| 对门（对面） | (i+3) mod 6（**对方阵营**）|
| 联邦（同队队友，2 名） | (i+2) mod 6, (i+4) mod 6 |
| 上下家 | (i-1) mod 6, (i+1) mod 6 |
| 对家 | 同"联邦"，本阶段两个联邦都视为对家 |

> **重要**：让牌仅在"上家是对家（同队联邦）"时可用；过牌后"对门(=i+3)"出够级牌可重新大过（见第 6 节）。

---

### 5. 买3 / 买4（本阶段实现，全自动）

**触发时机**：发牌后立刻进行（顺序：发牌 → 买3 → [Phase2: 进贡] → 买4 → 正式出牌）

**优先级（按顺序找卖家）**：
1. 对门 (i+3)
2. 联邦 (i+2), (i+4)（任一有多余即可）
3. 上下家 (i+1), (i-1)（任一有多余即可）

**代价规则（全自动）**：
- 卖家是**联邦** → "送 3"，免费拿走，卖家直接失去 1 张 3
- 卖家是**非联邦** → 买家按以下顺序付出 1 张牌：
  1. 优先付 1 张 2
  2. 无 2 → 付 1 张小王
  3. 无小王 → 付 1 张大王
  4. 无王无 2 → 直接拿（免费）
- 付出的牌从买家手牌移除，进入卖家手牌

**买 3 算法**：

```python
def execute_buy_3(players, np_random):
    """每人必须有1张3。多余3的玩家把多余3卖给没3的玩家。"""
    # 谁缺谁多
    counts = [count_rank(p.hand, '3') for p in players]
    buyers = [i for i, c in enumerate(counts) if c == 0]
    sellers = [i for i, c in enumerate(counts) if c > 1]   # 可卖数 = c - 1

    available = {s: counts[s] - 1 for s in sellers}

    for buyer in buyers:
        seller = pick_seller_by_priority(buyer, available)
        # priority: 对门 → 联邦(2,4) → 上下家(±1)
        execute_one_trade(buyer, seller, players)
        available[seller] -= 1
        if available[seller] == 0:
            del available[seller]
```

`execute_one_trade(buyer, seller, players)`：
- 把 1 张 3 从 seller 手牌移入 buyer 手牌
- 按规则确定代价（联邦免费；非联邦优先用 2，再小王，再大王，否则免费）
- 把代价牌从 buyer 移入 seller（如有）

**买 4**（与买3相同逻辑，但有特殊约束）：
- 只在玩家**完全没有 4** 时执行
- 可"放弃买"——本阶段简化为：**只要有人多余 4 就一定买**（跨局点贡留 Phase 2）
- 复用同一个 `execute_buy(rank='4', ...)` 通用函数

### 出牌约束（来自买3买4规则）

修改 `Judger.is_valid_play(cards, hand, round_state)` 增加：

1. **3 的约束**：
   - 3 必须**最后一手**单独打出（手牌只剩 1 张 3 时才能出 3）
   - 即：cards 中含 3 → 必须 (hand 仅剩这张 3) AND (cards 仅 1 张 3 且无其它牌)
   
2. **4 的约束**：
   - 玩家持有的所有 4 必须**一次出完**（`core_rank=4` 时，`core_count == 持有4的总数`）
   - 4 不能贴 2（attach_2 必须为 0）
   - 4 不能挂王（attach_BJ + attach_RJ + attach_Y 必须为 0）

```python
def is_valid_play_with_constraints(cards, hand, round_state):
    if not GoujiJudger.is_valid_play(cards, hand): return False
    play = parse_play(cards)
    
    # 3 的约束
    if play.core_rank == RANK_INDEX['3']:
        if len(hand) != 1: return False  # 必须是最后一张
        if play.total() != 1: return False  # 单独
    
    # 任何牌中混有 3（理论不可能，因为 core 必须同 rank）
    # 但 attach_2/attach_wang 不会有 3，所以只需检查 core
    
    # 4 的约束
    if play.core_rank == RANK_INDEX['4']:
        n4_in_hand = sum(1 for c in hand if c.rank == '4')
        if play.core_count != n4_in_hand: return False  # 必须一次全出
        if play.attach_2 > 0: return False
        if play.attach_BJ + play.attach_RJ + play.attach_Y > 0: return False
    
    return True
```

---

### 6. 让牌 / 过牌 / 出牌 状态机（本阶段实现）

#### 6.1 玩家本轮状态（5种）

```python
class PlayerRoundStatus(IntEnum):
    LEADING = 0   # 本轮发牌权拥有者，待出牌
    ACTIVE  = 1   # 待行动（决策：出/过/让）
    PLAYED  = 2   # 已出过牌
    PASSED  = 3   # 已过牌（本轮原则上不能再出，除非例外）
    YIELDED = 4   # 已让牌（仅状态标记，按用户确认）
```

#### 6.2 三种动作（统一字符串表示）

`legal_actions` 返回的是字符串集合，由智能体选择：

| 动作字符串 | 含义 |
|------------|------|
| `'pass'` | 过牌 |
| `'yield'` | 让牌（仅在上家为对家时可选）|
| `cards2str(cards)` | 出具体一组牌（如 `'7\|7\|7\|7'`、`'2\|7\|7\|7\|7'` 等）|

> 实现要点：因为 `cards2str` 不会出现 'pass'/'yield'，三类动作天然不冲突。

#### 6.3 让牌的可用条件

```python
def can_yield(player_id, round_state):
    return (round_state.last_player_id is not None
            and round_state.last_player_id != player_id
            and same_team(round_state.last_player_id, player_id)
            and round_state.player_status[player_id] == ACTIVE)
```

#### 6.4 出牌后状态自动转换

任何人出新牌（PLAYED）后：
- 所有 `YIELDED` 玩家自动变 `PASSED`（按用户的"让牌仅为状态标记"答复）

#### 6.5 过牌后的够级牌例外（本阶段实现）

PDF 原文：
> 过牌后，此轮牌不可再大过其他人，**除非对门打出够级牌或对门一套牌其他人均未大过**。

本阶段实现 2 种例外，重新激活 `PASSED` 玩家：

**例外A：对门出够级牌**
```python
# 触发条件：玩家 P 的对门 (P+3)%6 出了一张 is_gouji=True 的牌
if play.is_gouji() and player_status[P] == PASSED:
    if (P + 3) % 6 == player_who_just_played:
        player_status[P] = ACTIVE  # 重启
```

**例外B：对门牌其他人均未大过**
```python
# 当轮次走到某玩家时，如果当前 last_play 是其对门所出，
# 且除该玩家、其对门外其他 4 人都已 PASSED/YIELDED → 该玩家 PASSED 状态可重启
def maybe_reactivate(player_id, round_state):
    last_pid = round_state.greater_player_id
    if last_pid != (player_id + 3) % 6: return
    others = [i for i in range(6) if i != player_id and i != last_pid]
    if all(round_state.player_status[i] in (PASSED, YIELDED) for i in others):
        if round_state.player_status[player_id] == PASSED:
            round_state.player_status[player_id] = ACTIVE
```

#### 6.6 轮次切换逻辑（伪代码）

```python
def advance_turn(round_state):
    """切到下一个需要决策的玩家。
    优先逆时针寻找 ACTIVE 玩家；若无 ACTIVE 但有 YIELDED → 该玩家决策；
    若都无，本轮结束。
    """
    # 1) 先按例外B检查能否重启 PASSED 玩家
    for pid in range(6):
        maybe_reactivate(pid, round_state)
    
    # 2) 沿逆时针找 ACTIVE
    n = round_state.current_player_id
    for offset in range(1, 7):
        next_id = (n - offset) % 6   # 逆时针 = 减
        if round_state.player_status[next_id] == ACTIVE:
            round_state.current_player_id = next_id
            return False  # 还有人决策
    
    # 3) 找 YIELDED 决策
    for offset in range(1, 7):
        next_id = (n - offset) % 6
        if round_state.player_status[next_id] == YIELDED:
            round_state.current_player_id = next_id
            return False
    
    # 4) 都没了，本轮结束
    return True   # round over
```

#### 6.7 本轮结束 → 谁发下一轮

- `greater_player_id`（最后一个出牌的人）获得牌权 → 成为下一轮的 LEADING
- 重置所有玩家状态：LEADING + ACTIVE×5
- `last_play = None`

---

## 文件结构

```
rlcard/games/gouji/
├── __init__.py
├── utils.py            # 牌的编码 + 常量 + 工具函数 + 座位关系
├── judger.py           # 牌型解析与比牌（核心）
├── player.py           # 玩家状态（hand, team_id, played, round_status）
├── dealer.py           # 6副牌+6张鹰发牌（每人52张）
├── buy_phase.py        # 买3/买4 自动执行（新增）
├── round.py            # 轮次状态机（让牌/过牌/出牌+够级例外）
└── game.py             # 游戏主流程：发牌 → 买3 → 买4 → 多轮出牌

rlcard/envs/gouji.py    # 状态空间 + 环境

tests/games/test_gouji_utils.py
tests/games/test_gouji_judger.py
tests/games/test_gouji_buy_phase.py     # 新增
tests/games/test_gouji_round.py         # 新增（让牌/过牌状态机）
tests/games/test_gouji_game.py
tests/envs/test_gouji_env.py
```

**修改已有：**

- `rlcard/envs/env.py`: `supported_envs` 加 `'gouji'`
- `rlcard/envs/__init__.py`: 加 `from .gouji import GoujiEnv`
- `rlcard/games/__init__.py`: 加 gouji 注册

---

## 第一步：utils.py（编码 & 常量）

```python
# rlcard/games/gouji/utils.py
import numpy as np
from collections import Counter

# 16个等级（含 Y 鹰），索引 0-15
RANK_STR  = ['3','4','5','6','7','8','9','T','J','Q','K','A','2','BJ','RJ','Y']
RANK_INDEX = {r: i for i, r in enumerate(RANK_STR)}

SUIT_STR = ['S','H','D','C']

# 贴/挂牌：2、小王、大王、鹰均不参与 core 同点判断
ATTACH_RANKS = {'2', 'BJ', 'RJ', 'Y'}
WANG_RANKS   = {'BJ', 'RJ', 'Y'}      # 三种"王/鹰"

# 状态编码维度（合并花色后）
NUM_RANKS = 16
# 各 rank 的全局最大可能数量（用于归一化）
RANK_MAX_COUNT = {
    '3': 6,                                                 # 6张3
    '4': 24, '5': 24, '6': 24, '7': 24, '8': 24, '9': 24,   # 6副×4花色
    'T': 24, 'J': 24, 'Q': 24, 'K': 24, 'A': 24, '2': 24,
    'BJ': 6, 'RJ': 6, 'Y': 6,                                # 各6张
}

def hand_to_rank_array(hand: list) -> np.ndarray:
    """手牌 → 16维 rank 计数向量（合并花色，arr[i] = 该 rank 的张数）。"""
    arr = np.zeros(NUM_RANKS, dtype=np.int32)
    for card in hand:
        arr[RANK_INDEX[card.rank]] += 1
    return arr

def hand_to_normalized_array(hand: list) -> np.ndarray:
    """归一化的 rank 计数（除以该 rank 的最大可能数）→ 浮点 [0, 1]。"""
    arr = hand_to_rank_array(hand).astype(np.float32)
    for i, rank in enumerate(RANK_STR):
        arr[i] /= RANK_MAX_COUNT[rank]
    return arr

def get_rank_index(card) -> int:
    return RANK_INDEX[card.rank]

def is_attach_card(card) -> bool:
    return card.rank in ATTACH_RANKS

def is_wang(card) -> bool:
    return card.rank in WANG_RANKS

def cards2str(cards: list) -> str:
    """统一字符串表示：小写 'y' 表示鹰，方便和 BJ/RJ 区分；
    Card 列表 → 按 rank 排序后拼接 rank.first_char 或全名。"""
    # 简化：直接用 rank 名拼接，按 rank_index 排序
    sorted_cards = sorted(cards, key=get_rank_index)
    return '|'.join(c.rank for c in sorted_cards)
```

### 鹰的 Card 表示

`rlcard/games/base.py` 中已有 `Card(suit, rank)`，鹰可用 `Card('', 'Y')`（空花色 + rank='Y'），与 BJ/RJ 同型处理。

---

## 第二步：judger.py（牌型检验，核心）

### Play 数据结构

```python
# rlcard/games/gouji/judger.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Play:
    """一次出牌的结构化解析结果。"""
    core_rank: int          # 核心点数（0-15）；-1=无核心（仅作内部边界，正常解析不出现）
    core_count: int         # 核心牌张数
    attach_2: int           # 贴 2 数量（rank='2' 的张数，可贴钱）
    attach_BJ: int          # 小王挂数
    attach_RJ: int          # 大王挂数
    attach_Y: int           # 鹰挂数
    is_pass: bool = False   # 是否过牌

    def total(self) -> int:
        return self.core_count + self.attach_2 + self.attach_BJ + self.attach_RJ + self.attach_Y

    def wang_list_desc(self) -> list:
        """所有挂的王/鹰按级别降序排列，用于 can_beat 的逐位严格管比较。
        Y=15, RJ=14, BJ=13"""
        return ([RANK_INDEX['Y']] * self.attach_Y +
                [RANK_INDEX['RJ']] * self.attach_RJ +
                [RANK_INDEX['BJ']] * self.attach_BJ)

    def is_gouji(self) -> bool:
        """是否够级牌：含挂画 OR 满足够级数量门槛。"""
        if self.attach_BJ + self.attach_RJ + self.attach_Y > 0:
            return True
        # 纯/贴2牌型按门槛判断
        eff = self.core_count + self.attach_2
        if self.core_rank == RANK_INDEX['T'] and eff >= 5: return True
        if self.core_rank == RANK_INDEX['J'] and eff >= 4: return True
        if self.core_rank == RANK_INDEX['Q'] and eff >= 3: return True
        if self.core_rank == RANK_INDEX['K'] and eff >= 2: return True
        if self.core_rank == RANK_INDEX['A'] and eff >= 2: return True
        if self.core_rank == RANK_INDEX['2'] and eff >= 1: return True
        return False
```

### GoujiJudger 接口

```python
class GoujiJudger:

    @staticmethod
    def parse_play(cards: list) -> Play:
        """
        将出牌 Card 列表解析成 Play，规则（已与用户确认）：

          【纯core 规则】如果所有牌的 rank 完全相同 → 解析为纯 core，无 attach
            - 7777 → core_rank=7, count=4
            - 222 → core_rank=2, count=3 (rank索引=12)
            - 三大王 → core_rank=RJ, count=3 (rank索引=14)
            - 三小王 → core_rank=BJ, count=3 (rank索引=13)
            - 三鹰 → core_rank=Y, count=3 (rank索引=15)

          【混合 规则】否则按以下分层处理：
            1) 分离王/鹰 → attach_BJ / attach_RJ / attach_Y
            2) 在剩余牌中：分离 2 → attach_2 候选；剩下的为 non-2 非王
            3) non-2 非王 必须全部相同 rank → core_rank, core_count
            4) 若 non-2 非王 为空：
                 - 若有 2 → core_rank=12('2'), core_count=len(2s), attach_2=0
                 - 若只有王/鹰且全是同一种 → 已在【纯core】处理
                 - 否则（混合王/鹰，无 core）→ 当前 v2 暂不允许，抛 ValueError
                   （如需支持纯王混合，core_rank=-1 + 全部作 attach；但需在 can_beat
                    特殊处理"core_rank=-1 双方"的情况）

        合法性约束：
          - non-2 非王 中不能含多个 rank
          - 不能空牌
        """

    @staticmethod
    def is_valid_play(cards: list, hand: list) -> bool:
        """
        合法性检查：
          - 手牌多重集包含
          - parse_play 不抛错
          - 至少 1 张
        """

    @staticmethod
    def can_beat(new_cards: list, current_play: Play) -> bool:
        """
        new_cards 能否压过 current_play（最终版规则）：
          1. 解析 → new_play；若 is_pass 直接 False
          2. total() 必须相等
          3. current_play.attach_Y > 0 → 鹰挂不可被压，直接 False
          4. 王覆盖：把双方的王/鹰按级别降序排列
                len(cur_wangs) > len(new_wangs)         → False（王不够覆盖）
                exist i: new_wangs[i] < cur_wangs[i]    → False（第i位没被覆盖）
          5. core_rank 严格更大 → True；否则 False
        """

    @staticmethod
    def playable_cards_from_hand(hand: list, last_play: Optional[Play],
                                  round_state=None) -> set:
        """
        枚举手牌中所有合法出牌（返回字符串集合，类似斗地主的 action 字符串）。

        last_play=None：表示本轮第一手（发牌），枚举所有 parse_play 成功的组合
        last_play 非空：枚举所有能 can_beat 的组合，外加 'pass'

        round_state（本阶段新增）：用于 3/4 约束、yield 可用性判断
          - 若可让牌（上家是对家） → 加入 'yield'
          - 应用 3/4 约束过滤（3 必须最后一手；4 必须一次全出且不挂2/王）

        枚举步骤：
          a. 分组：non_attach_groups[rank] = [Card列表]，attach_2_pool, BJ_pool, RJ_pool, Y_pool
          b. 对每个 (rank_group, core_count in 1..持有数):
               生成 core 组合（花色不同视为同型，去重）
               for n2, nBJ, nRJ, nY in 各贴/挂池的组合（含0）：
                  组装 cards，加入 candidate
                  if last_play is None or can_beat(cards, last_play): add
          c. 单独枚举：core 是 2（全2）的情况
          d. 单独枚举：纯单类王（三大王、二小王 等，作纯core）
          e. last_play 非空时加 'pass'
          f. 满足 can_yield 时加 'yield'
          g. 应用 3/4 约束过滤（is_valid_play_with_constraints）

        减枝：相同点数选哪几张花色，对牌型本身没有影响（不考虑花色），可只取一种花色组合。
        """

    @staticmethod
    def judge_game(players) -> int:
        """返回赢家队伍编号（0或1），未结束返 -1。"""

    @staticmethod
    def judge_payoffs(winner_team: int, num_players: int = 6) -> np.ndarray:
        """6人收益：赢家队伍+1，输家-1。team0 = {0,2,4}, team1 = {1,3,5}"""
```

### parse_play 算法详细伪代码

```python
def parse_play(cards):
    if len(cards) == 0:
        return Play(core_rank=-1, core_count=0, attach_2=0,
                    attach_BJ=0, attach_RJ=0, attach_Y=0, is_pass=True)

    # 【纯core 优先检查】所有牌 rank 完全相同
    ranks_set = set(c.rank for c in cards)
    if len(ranks_set) == 1:
        only_rank = ranks_set.pop()
        return Play(
            core_rank=RANK_INDEX[only_rank],
            core_count=len(cards),
            attach_2=0, attach_BJ=0, attach_RJ=0, attach_Y=0,
        )

    # 【混合 规则】
    BJs = [c for c in cards if c.rank == 'BJ']
    RJs = [c for c in cards if c.rank == 'RJ']
    Ys  = [c for c in cards if c.rank == 'Y']
    twos = [c for c in cards if c.rank == '2']
    others = [c for c in cards if c.rank not in {'2','BJ','RJ','Y'}]

    if len(others) == 0:
        # 没有 non-2 非王
        if len(twos) > 0:
            # 2 + 王/鹰 → 2 当 core
            return Play(
                core_rank=RANK_INDEX['2'],
                core_count=len(twos),
                attach_2=0,
                attach_BJ=len(BJs), attach_RJ=len(RJs), attach_Y=len(Ys),
            )
        else:
            # 全是混合王/鹰（无 2、无 core）
            # v2 暂不支持，后续如需开放再加
            raise ValueError(f'混合纯王/鹰组合暂不支持: {[c.rank for c in cards]}')

    # 有 non-2 非王 core
    others_ranks = set(c.rank for c in others)
    if len(others_ranks) > 1:
        raise ValueError(f'core 含多种点数: {[c.rank for c in others]}')
    core_rank_str = others_ranks.pop()

    return Play(
        core_rank=RANK_INDEX[core_rank_str],
        core_count=len(others),
        attach_2=len(twos),       # 贴2（其点数<2，2视为core_rank）
        attach_BJ=len(BJs),
        attach_RJ=len(RJs),
        attach_Y=len(Ys),
    )
```

### can_beat 实现

```python
def can_beat(new_cards, current_play):
    new_play = GoujiJudger.parse_play(new_cards)
    if new_play.is_pass:
        return False

    # 1. 总张数相同
    if new_play.total() != current_play.total():
        return False

    # 2. 鹰挂不可被压
    if current_play.attach_Y > 0:
        return False

    # 3. 王覆盖：逐位严格管
    cur_wangs = sorted(current_play.wang_list_desc(), reverse=True)
    new_wangs = sorted(new_play.wang_list_desc(), reverse=True)
    if len(cur_wangs) > len(new_wangs):
        return False
    for i in range(len(cur_wangs)):
        if new_wangs[i] < cur_wangs[i]:
            return False

    # 4. core_rank 严格更大
    return new_play.core_rank > current_play.core_rank
```

---

## 第三步：状态空间 envs/gouji.py

### 观察向量布局（**135维**，按 rank 合并花色）

```
[0:16]         self_hand_rank                    16  自己手牌按 rank 计数（归一化）
[16:96]        others_played_rank[5] × 16        80  其他5位玩家累计已出（按 rank）
[96:102]       remaining_cards / 52              6   各玩家剩余牌数
[102:118]      last_play_array_rank              16  当前轮最后有效出牌（按 rank）
[118:123]      last_play 元数据                  5
                 [core_rank/15, core_count/52,
                  attach_2/52, attach_wangs_total/18, is_gouji 0/1]
[123:129]      最后出牌者位置 one-hot (6维)       6
[129:135]      6 玩家本轮状态                     6
                 每位玩家 1 维 = status / 4 (0..1)
                 0=LEADING, 1=ACTIVE, 2=PLAYED, 3=PASSED, 4=YIELDED
─────────────────────────────────────────────────────
合计                                              135
```

> attach_wangs_total 上限是 18（6 BJ + 6 RJ + 6 Y）。
> 计数向量用 `hand_to_normalized_array`：除以该 rank 的最大可能数（让数值范围统一在 [0,1]）。

> 烧牌、四户乱缠、无头、要头等高级状态是 Phase 2 的内容。

### 环境实现

```python
# rlcard/envs/gouji.py
import numpy as np
from collections import OrderedDict
from rlcard.envs import Env
from rlcard.games.gouji import Game as GoujiGame
from rlcard.games.gouji.utils import (
    NUM_RANKS, hand_to_normalized_array, hand_to_rank_array, RANK_INDEX
)

OBS_DIM = 135

class GoujiEnv(Env):
    name = 'gouji'

    def __init__(self, config=None):
        self.name = 'gouji'
        self.default_game_config = {}
        self.game = GoujiGame()
        super().__init__(config or {})
        self.num_players = 6
        self.state_shape  = [[OBS_DIM] for _ in range(6)]
        self.action_shape = [None for _ in range(6)]

    def _extract_state(self, raw_state):
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        obs[0:16] = raw_state['current_hand_arr']
        for i, arr in enumerate(raw_state['others_played_arr']):
            obs[16 + i*16 : 16 + (i+1)*16] = arr
        obs[96:102] = np.array(raw_state['num_cards_left'], dtype=np.float32) / 52.0
        obs[102:118] = raw_state['last_play_array']

        lp = raw_state['last_play_meta']
        obs[118] = lp['core_rank'] / 15.0 if lp['core_rank'] >= 0 else -1.0
        obs[119] = lp['core_count'] / 52.0
        obs[120] = lp['attach_2'] / 52.0
        obs[121] = lp['attach_wangs_total'] / 18.0
        obs[122] = float(lp['is_gouji'])

        last_pid = raw_state['last_player_id']
        if last_pid is not None:
            obs[123 + last_pid] = 1.0

        # 6位玩家状态：每人一个浮点（status/4），共 6 维
        for i, status in enumerate(raw_state['player_round_status']):
            obs[129 + i] = int(status) / 4.0

        legal_actions = OrderedDict({a: None for a in raw_state['actions']})
        return {
            'obs': obs,
            'legal_actions': legal_actions,
            'raw_obs': raw_state,
            'raw_legal_actions': list(raw_state['actions']),
            'action_record': self.action_recorder,
        }

    def _decode_action(self, action_id):
        return self.game.actions_lookup[action_id]

    def get_payoffs(self):
        return self.game.judger.judge_payoffs(self.game.winner_team)
```

### Game.get_state 应返回的 raw_state 字段

```python
{
    'current_hand_arr': np.ndarray(16),              # rank 计数（归一化）
    'others_played_arr': [np.ndarray(16)] * 5,       # 按相对座次顺序
    'num_cards_left': [int] * 6,
    'last_play_array': np.ndarray(16),
    'last_play_meta': {
        'core_rank': int,
        'core_count': int,
        'attach_2': int,
        'attach_wangs_total': int,
        'is_gouji': bool,
    },
    'last_player_id': Optional[int],
    'player_round_status': [int] * 6,
    'actions': list[str],
    'self': int,
    'team_id': int,
}
```

---

## 第四步：dealer.py / buy_phase.py / round.py / game.py

### Dealer：发牌（与之前相同）

```python
class GoujiDealer:
    def __init__(self, np_random):
        self.np_random = np_random
        self.deck = self._init_deck()    # 312张

    def _init_deck(self):
        cards = []
        # 6副普通牌
        for _ in range(6):
            for suit in SUIT_STR:
                for rank in ['3','4','5','6','7','8','9','T','J','Q','K','A','2']:
                    cards.append(Card(suit, rank))
            cards.append(Card('', 'BJ'))
            cards.append(Card('', 'RJ'))
        # 移除多余的 3，只留 6 张（每人 1 张）
        threes = [c for c in cards if c.rank == '3']
        non_threes = [c for c in cards if c.rank != '3']
        keep_threes = self.np_random.choice(threes, 6, replace=False).tolist()
        cards = non_threes + keep_threes
        # 加 6 张鹰
        cards += [Card('', 'Y') for _ in range(6)]
        assert len(cards) == 312
        return cards

    def shuffle(self):
        self.np_random.shuffle(self.deck)

    def deal(self, players):
        """每人 52 张。3 的分配在洗牌后随机分给每人 0+ 张，由 buy_phase 修复 1 张约束。"""
        self.np_random.shuffle(self.deck)
        for i, p in enumerate(players):
            p.hand = self.deck[i*52 : (i+1)*52]
```

### buy_phase.py：买3 / 买4

```python
# rlcard/games/gouji/buy_phase.py
from .utils import RANK_INDEX

# 同队队友 = 联邦
def is_lianbang(p1: int, p2: int) -> bool:
    return (p1 - p2) % 2 == 0 and p1 != p2

# 对门
def is_duimen(p1: int, p2: int) -> bool:
    return (p1 + 3) % 6 == p2

def buyer_priority(buyer: int) -> list:
    """优先级顺序的卖家ID列表（按 PDF：对门 → 联邦 → 上下家）"""
    return [
        (buyer + 3) % 6,         # 对门
        (buyer + 2) % 6, (buyer + 4) % 6,  # 联邦
        (buyer + 1) % 6, (buyer - 1) % 6,  # 上下家
    ]

def execute_buy(rank: str, players, np_random) -> None:
    """通用买货：使每个玩家至少有1张该 rank 的牌（如果可能）。
    
    买 3：所有缺3玩家自动买（必须）。
    买 4：所有缺4玩家自动买（本阶段简化为：能买就买）。
    """
    counts = [sum(1 for c in p.hand if c.rank == rank) for p in players]
    available = {i: counts[i] - 1 for i in range(6) if counts[i] >= 2}
    buyers = [i for i in range(6) if counts[i] == 0]

    for buyer in buyers:
        for cand in buyer_priority(buyer):
            if available.get(cand, 0) > 0:
                _trade(buyer, cand, rank, players)
                available[cand] -= 1
                if available[cand] == 0:
                    del available[cand]
                break
        # 若没有任何卖家可用，跳过（约束允许少数玩家无对应 rank）

def _trade(buyer_id: int, seller_id: int, rank: str, players) -> None:
    """从卖家移走 1 张该 rank 给买家；按规则确定代价付出。"""
    buyer, seller = players[buyer_id], players[seller_id]
    
    # 找一张该 rank 移给 buyer
    target_card = next(c for c in seller.hand if c.rank == rank)
    seller.hand.remove(target_card)
    buyer.hand.append(target_card)
    
    # 联邦免费
    if is_lianbang(buyer_id, seller_id):
        return
    
    # 非联邦：buyer 付代价（2 → BJ → RJ）
    for cost_rank in ['2', 'BJ', 'RJ']:
        cost = next((c for c in buyer.hand if c.rank == cost_rank), None)
        if cost is not None:
            buyer.hand.remove(cost)
            seller.hand.append(cost)
            return
    # buyer 无 2 / 王 → 直接拿（免费）
```

### Round：轮次状态机

```python
# rlcard/games/gouji/round.py
from enum import IntEnum
from .judger import Play, GoujiJudger

class PlayerRoundStatus(IntEnum):
    LEADING = 0
    ACTIVE  = 1
    PLAYED  = 2
    PASSED  = 3
    YIELDED = 4

class GoujiRound:
    def __init__(self):
        self.last_play: Optional[Play] = None
        self.last_player_id: Optional[int] = None     # 最近有效出牌者
        self.greater_player_id: Optional[int] = None  # 当前最大牌拥有者
        self.current_player_id: int = 0
        self.player_status: list = [PlayerRoundStatus.ACTIVE] * 6
        self.player_status[0] = PlayerRoundStatus.LEADING

    def proceed(self, action: str, parsed_play: Optional[Play], players):
        """处理一次动作。返回是否本轮结束。"""
        pid = self.current_player_id
        
        if action == 'pass':
            self.player_status[pid] = PlayerRoundStatus.PASSED
        elif action == 'yield':
            self.player_status[pid] = PlayerRoundStatus.YIELDED
        else:
            # 出牌
            self.last_play = parsed_play
            self.last_player_id = pid
            self.greater_player_id = pid
            self.player_status[pid] = PlayerRoundStatus.PLAYED
            # 把所有 YIELDED 自动变 PASSED
            for i in range(6):
                if self.player_status[i] == PlayerRoundStatus.YIELDED:
                    self.player_status[i] = PlayerRoundStatus.PASSED
            # 够级牌例外A：对门重启
            if parsed_play.is_gouji():
                duimen = (pid + 3) % 6
                if self.player_status[duimen] == PlayerRoundStatus.PASSED:
                    self.player_status[duimen] = PlayerRoundStatus.ACTIVE

        return self._advance_turn()

    def _advance_turn(self) -> bool:
        """切到下一个待决策的玩家；返回 True 若本轮结束。"""
        # 例外B：对门牌其他人均未压 → 重启
        if self.greater_player_id is not None:
            for pid in range(6):
                if self.player_status[pid] == PlayerRoundStatus.PASSED:
                    if (pid + 3) % 6 == self.greater_player_id:
                        others = [i for i in range(6) if i != pid and i != self.greater_player_id]
                        if all(self.player_status[i] in
                               (PlayerRoundStatus.PASSED, PlayerRoundStatus.YIELDED)
                               for i in others):
                            self.player_status[pid] = PlayerRoundStatus.ACTIVE

        # 逆时针找 ACTIVE / LEADING
        n = self.current_player_id
        for offset in range(1, 7):
            nxt = (n - offset) % 6
            if self.player_status[nxt] in (
                PlayerRoundStatus.ACTIVE, PlayerRoundStatus.LEADING
            ):
                self.current_player_id = nxt
                return False

        # 找 YIELDED
        for offset in range(1, 7):
            nxt = (n - offset) % 6
            if self.player_status[nxt] == PlayerRoundStatus.YIELDED:
                self.current_player_id = nxt
                return False
        
        return True   # 本轮结束

    def reset_for_next_round(self):
        """获得牌权的玩家成为新一轮 LEADING。"""
        new_leader = self.greater_player_id
        self.last_play = None
        self.last_player_id = None
        self.greater_player_id = None
        self.player_status = [PlayerRoundStatus.ACTIVE] * 6
        self.player_status[new_leader] = PlayerRoundStatus.LEADING
        self.current_player_id = new_leader
```

### Game：主流程

```python
class GoujiGame:

    def __init__(self, allow_step_back=False):
        self.num_players = 6
        self.allow_step_back = allow_step_back

    def init_game(self):
        self.players = [GoujiPlayer(i) for i in range(6)]
        self.dealer  = GoujiDealer(self.np_random)
        self.dealer.shuffle()
        self.dealer.deal(self.players)
        # 买 3
        from .buy_phase import execute_buy
        execute_buy('3', self.players, self.np_random)
        # 买 4（本阶段：能买就买）
        execute_buy('4', self.players, self.np_random)
        # 进贡（Phase 2）
        
        self.judger  = GoujiJudger()
        self.round   = GoujiRound()
        self.round.current_player_id = 0   # 简化：玩家0先发牌（Phase2: 上班/抢班/大落）
        self.round.player_status[0] = PlayerRoundStatus.LEADING
        self.winner_team = -1
        return self.get_state(0), 0

    def step(self, action: str):
        """action 字符串可为 'pass' / 'yield' / cards2str(cards)"""
        # 1) 解析 action：拆出动作类型
        # 2) 若为出牌：校验合法性（通过 player.hand 和 round.last_play 及 3/4 约束）
        # 3) 应用：从手牌移除、加入 played
        # 4) round.proceed(action, parsed_play, players) 处理状态机 + 例外重启
        # 5) 检查 is_over：若有人空牌，记录 winner_team
        # 6) 若 round 结束：round.reset_for_next_round()
        ...

    def is_over(self):
        return self.winner_team != -1

    def get_state(self, player_id):
        """构造 raw_state（见上方 envs 章节）"""
        ...
```

> **本阶段简化（已与用户确认）**：
> 
> - 出牌顺序：逆时针（id 递减 mod 6）
> - 第一手由玩家 0 发牌（Phase2: 上班/抢班/大落）
> - **包含**：买3、买4（自动）、3/4 出牌约束、让牌、过牌、过牌后够级牌例外（A/B 两种）
> - **不含 Phase 2 内容**：走科顺序与接风、被闷、进贡、革命、冲点、要头/无头、烧牌、四户乱缠、开点判定、跨局点贡、圈三户、汇5

---

## 实现顺序 & TodoWrite

```
1. utils.py             (常量、card_to_index、hand_to_array、座位关系函数)
2. judger.py 1/3        (Play、parse_play、can_beat)
3. test_gouji_judger.py 1/2  (parse_play / can_beat 基础测试，含用户例子)
4. judger.py 2/3        (is_gouji + is_valid_play_with_constraints 3/4约束)
5. judger.py 3/3        (playable_cards_from_hand 枚举)
6. test_gouji_judger.py 2/2  (够级牌 + 出牌约束)
7. player.py            (Player 数据类 + team_id)
8. dealer.py            (312张牌、洗牌、发牌)
9. buy_phase.py         (execute_buy 通用买货 + _trade)
10. test_gouji_buy_phase.py
11. round.py            (PlayerRoundStatus + GoujiRound 状态机)
12. test_gouji_round.py (让牌/过牌/够级例外)
13. game.py             (init_game 含买3/买4 + step + get_state)
14. envs/gouji.py       (_extract_state, 135维状态 + 注册)
15. test_gouji_game.py + test_gouji_env.py (端到端)
```

---

## 关键测试用例

### test_gouji_utils.py

- `card_to_index('S','3')` 等 → 各唯一索引正确
- 鹰索引 = 54
- `hand_to_array` 计数正确
- `is_lianbang(0,2)`=True, `is_lianbang(0,1)`=False, `is_duimen(0,3)`=True

### test_gouji_judger.py（**最关键**）

```python
# parse_play 基础
def test_parse_pure():
    p = parse([Card('S','7'), Card('H','7')])
    assert (p.core_rank, p.core_count, p.attach_2, p.attach_BJ, p.attach_RJ, p.attach_Y) \
           == (RANK_INDEX['7'], 2, 0, 0, 0, 0)

def test_parse_attach2():
    # 27777 → core=7777, attach_2=1
    p = parse([Card('S','2'), Card('S','7'), Card('H','7'), Card('D','7'), Card('C','7')])
    assert p.core_rank == RANK_INDEX['7']
    assert p.core_count == 4 and p.attach_2 == 1
    assert p.total() == 5

def test_parse_wang_attach():
    # 小王7777 → core=7777, attach_BJ=1
    p = parse([Card('','BJ'), Card('S','7'), Card('H','7'), Card('D','7'), Card('C','7')])
    assert p.core_count == 4 and p.attach_BJ == 1

def test_parse_pure_2():
    # 全是2 → core_rank=2, count=2 (纯core)
    p = parse([Card('S','2'), Card('H','2')])
    assert p.core_rank == RANK_INDEX['2'] and p.core_count == 2 and p.attach_2 == 0

def test_parse_pure_wang_single_type():
    # 三大王 → core_rank=RJ, count=3 (纯core)
    p = parse([Card('','RJ'), Card('','RJ'), Card('','RJ')])
    assert p.core_rank == RANK_INDEX['RJ'] and p.core_count == 3
    assert p.attach_BJ == 0 and p.attach_RJ == 0 and p.attach_Y == 0

def test_parse_pure_wang_eagle():
    # 三鹰 → core_rank=Y, count=3
    p = parse([Card('','Y')] * 3)
    assert p.core_rank == RANK_INDEX['Y'] and p.core_count == 3

def test_parse_2_with_wang():
    # 王22 → core=22, attach_BJ=1
    p = parse([Card('','BJ'), Card('S','2'), Card('H','2')])
    assert p.core_rank == RANK_INDEX['2']
    assert p.core_count == 2 and p.attach_BJ == 1 and p.attach_2 == 0

def test_invalid_mixed():
    with pytest.raises(ValueError):
        parse([Card('S','7'), Card('H','8')])

def test_invalid_pure_mixed_wangs():
    # v2 暂不支持纯混合王
    with pytest.raises(ValueError):
        parse([Card('','BJ'), Card('','RJ')])

# ───── can_beat 测试（基于用户确认的例子）─────

def _cur(cards):
    return GoujiJudger.parse_play(cards)

def test_88888_beats_27777():
    cur = _cur([Card('S','2'), *[Card(s,'7') for s in 'SHDC']])
    new = [Card('S','8'), Card('H','8'), Card('D','8'), Card('C','8'), Card('S','8')]
    assert can_beat(new, cur)

def test_22888_beats_27777():
    cur = _cur([Card('S','2'), *[Card(s,'7') for s in 'SHDC']])
    new = [Card('S','2'), Card('H','2'), Card('S','8'), Card('H','8'), Card('D','8')]
    assert can_beat(new, cur)

def test_wang2888_beats_27777():
    cur = _cur([Card('S','2'), *[Card(s,'7') for s in 'SHDC']])
    new = [Card('','BJ'), Card('S','2'), Card('S','8'), Card('H','8'), Card('D','8')]
    assert can_beat(new, cur)

# 用户例子1：小王挂7777 ↔ 大王挂6666 互不能压
def test_user_example1_dawang6666_cant_beat_xiaowang7777():
    cur = _cur([Card('','BJ'), *[Card(s,'7') for s in 'SHDC']])  # 小王7777
    new = [Card('','RJ'), *[Card(s,'6') for s in 'SHDC']]         # 大王6666
    # core 6 < 7 → 不能压
    assert not can_beat(new, cur)

def test_user_example1_xiaowang7777_cant_beat_dawang6666():
    cur = _cur([Card('','RJ'), *[Card(s,'6') for s in 'SHDC']])  # 大王6666
    new = [Card('','BJ'), *[Card(s,'7') for s in 'SHDC']]         # 小王7777
    # 王覆盖失败：BJ < RJ → 不能压
    assert not can_beat(new, cur)

# 用户例子2：小王2777 == 小王7777 (互不能压)
def test_user_example2_xiaowang2777_equals_xiaowang7777():
    p1 = _cur([Card('','BJ'), Card('S','2'), Card('S','7'), Card('H','7'), Card('D','7')])
    p2 = _cur([Card('','BJ'), Card('S','7'), Card('H','7'), Card('D','7'), Card('C','7')])
    # core_rank、wang_list、total 均相同 → 互不能压
    assert not can_beat([Card('','BJ'), Card('S','2'), Card('S','7'), Card('H','7'), Card('D','7')], p2)
    assert not can_beat([Card('','BJ'), Card('S','7'), Card('H','7'), Card('D','7'), Card('C','7')], p1)

# 用户例子3：222 必须三张王压
def test_user_example3_three_xiaowang_beats_222():
    cur = _cur([Card('S','2'), Card('H','2'), Card('D','2')])  # 222
    new = [Card('','BJ'), Card('','BJ'), Card('','BJ')]         # 三小王
    assert can_beat(new, cur)

def test_user_example3_three_dawang_beats_222():
    cur = _cur([Card('S','2'), Card('H','2'), Card('D','2')])  # 222
    new = [Card('','RJ'), Card('','RJ'), Card('','RJ')]         # 三大王
    assert can_beat(new, cur)

def test_user_example3_wang22_cant_beat_222():
    """关键：王22(BJ=1, core=2, total=3) vs 222(core=2, total=3) - 不能压"""
    cur = _cur([Card('S','2'), Card('H','2'), Card('D','2')])  # 222
    new = [Card('','BJ'), Card('S','2'), Card('H','2')]         # 王22
    # 王虽多，但 core_rank 相等不严格大 → 不能压
    assert not can_beat(new, cur)

# 鹰挂不可被压
def test_eagle_unbeatable():
    cur = _cur([Card('','Y'), *[Card(s,'A') for s in 'SHDC']])  # 鹰AAAA
    new = [Card('','Y'), *[Card(s,'2') for s in 'SHDC']]          # 鹰2222
    assert not can_beat(new, cur)  # 即便 core_rank 更大，鹰挂不可被压

# 王覆盖逐位严格管：两鹰挂999 压 一大一小挂888
def test_two_eagle_999_beats_dawang_xiaowang_888():
    cur = _cur([Card('','RJ'), Card('','BJ'), Card('S','8'), Card('H','8'), Card('D','8')])
    new = [Card('','Y'), Card('','Y'), Card('S','9'), Card('H','9'), Card('D','9')]
    # cur_wangs=[RJ,BJ], new_wangs=[Y,Y]; Y>=RJ Y>=BJ; core 9>8
    assert can_beat(new, cur)

def test_one_eagle_one_dawang_999_beats_dawang_xiaowang_888():
    cur = _cur([Card('','RJ'), Card('','BJ'), Card('S','8'), Card('H','8'), Card('D','8')])
    new = [Card('','Y'), Card('','RJ'), Card('S','9'), Card('H','9'), Card('D','9')]
    # cur_wangs=[RJ,BJ], new_wangs=[Y,RJ]; Y>=RJ, RJ>=BJ; core 9>8
    assert can_beat(new, cur)

# 同级别王 + core 严格更大可压
def test_xiaowang8888_beats_xiaowang7777():
    cur = _cur([Card('','BJ'), *[Card(s,'7') for s in 'SHDC']])
    new = [Card('','BJ'), *[Card(s,'8') for s in 'SHDC']]
    assert can_beat(new, cur)

# is_gouji 测试
def test_gouji_thresholds():
    assert parse([Card(s,'T') for s in 'SHDC'] + [Card('S','T')]).is_gouji()  # 5×10
    assert parse([Card(s,'J') for s in 'SHDC']).is_gouji()                     # 4×J
    assert parse([Card('S','2')]).is_gouji()                                   # 1×2
    assert not parse([Card('S','T'), Card('H','T')]).is_gouji()                # 2×10 不够
    assert parse([Card('','BJ'), Card('S','3')]).is_gouji()                    # 含挂画

    # 贴 2 也满足够级门槛
    p = parse([Card('S','2'), Card('S','T'), Card('H','T'), Card('D','T'), Card('C','T')])
    # 视为五个10 (eff=5) → 是够级牌
    assert p.is_gouji()
```

### test_gouji_judger.py 出牌约束（3/4）

```python
# 3 必须最后一手单独打
def test_three_must_be_last():
    hand = [Card('S','3'), Card('H','5')]
    # 只剩 3 + 5，出 3 不合法（手牌不止1张）
    assert not is_valid_play_with_constraints([Card('S','3')], hand, None)
    # 只剩单 3 → 合法
    assert is_valid_play_with_constraints([Card('S','3')], [Card('S','3')], None)

# 4 必须一次出完且不能挂
def test_four_must_all_once():
    hand = [Card('S','4'), Card('H','4'), Card('D','4'), Card('S','5')]
    # 仅出 1 张 4（没全出） → 不合法
    assert not is_valid_play_with_constraints([Card('S','4')], hand, None)
    # 全出 3 张 4 → 合法
    assert is_valid_play_with_constraints(
        [Card('S','4'),Card('H','4'),Card('D','4')], hand, None)

def test_four_no_attach():
    hand = [Card('S','4'), Card('H','4'), Card('S','2'), Card('','BJ')]
    # 4444 + 2 贴 → 不合法
    assert not is_valid_play_with_constraints(
        [Card('S','4'),Card('H','4'),Card('S','2')], hand, None)
    # 4444 + 王 → 不合法
    assert not is_valid_play_with_constraints(
        [Card('S','4'),Card('H','4'),Card('','BJ')], hand, None)
```

### test_gouji_buy_phase.py（新增）

```python
def test_buy_3_lianbang_free():
    """玩家0缺3，从联邦(玩家2)免费拿"""
    players = make_test_players()
    players[0].hand = [Card('S','5')]
    players[2].hand = [Card('S','3'), Card('H','3'), Card('S','7')]  # 多余1张3
    pre_p0 = list(players[0].hand)
    pre_p2 = list(players[2].hand)
    execute_buy('3', players, np_random)
    assert sum(1 for c in players[0].hand if c.rank == '3') == 1
    assert sum(1 for c in players[2].hand if c.rank == '3') == 1  # 卖家剩1张
    assert len(players[0].hand) == 2  # 拿回 1 张，没付代价
    assert len(players[2].hand) == 2  # 失去 1 张，没收代价

def test_buy_3_non_lianbang_with_2():
    """玩家0缺3，对门玩家3有多余3 → 必须用 2 买"""
    players = make_test_players()
    players[0].hand = [Card('S','5'), Card('H','2')]
    players[3].hand = [Card('S','3'), Card('H','3')]
    execute_buy('3', players, np_random)
    # 玩家0：失 2 得 3
    assert sum(1 for c in players[0].hand if c.rank == '3') == 1
    assert sum(1 for c in players[0].hand if c.rank == '2') == 0
    # 玩家3：失 3 得 2
    assert sum(1 for c in players[3].hand if c.rank == '3') == 1
    assert sum(1 for c in players[3].hand if c.rank == '2') == 1

def test_buy_priority_duimen_first():
    """对门有，联邦也有 → 优先从对门买"""
    ...

def test_buy_3_no_2_use_BJ():
    """非联邦买3，无 2 则付小王"""
    ...

def test_buy_3_free_when_no_cost():
    """非联邦买3，无 2/王 直接拿"""
    ...

def test_buy_4_executed():
    """买4走相同流程"""
    ...
```

### test_gouji_round.py（新增 - 让牌/过牌状态机）

```python
def test_pass_locks_player_in_round():
    """普通过牌后该玩家本轮不可再出"""
    rs = init_round(leader=0)
    rs.proceed('pass', None, players)  # 但 leader 不能 pass，假设玩家1过
    ...

def test_yield_only_when_partner_played():
    """让牌仅在上家是同队队友时可用"""
    rs = init_round(leader=0)
    # 玩家0出牌后，玩家2(联邦) 决策 → 可让牌
    # 玩家0出牌后，玩家1(对手) 决策 → 不可让牌
    ...

def test_yield_auto_becomes_pass_after_someone_plays():
    """让牌后任何人出牌 → 让牌自动变过牌"""
    rs = init_round(leader=0)
    # 玩家0出 [Card('S','7'), Card('H','7')]
    # 玩家2让牌 (status=YIELDED)
    # 玩家1出更大 [Card('S','8'), Card('H','8')] (status=PLAYED)
    # 验证 玩家2 现在 status=PASSED
    ...

def test_yield_resolves_to_choice_when_no_one_beats():
    """让牌后所有人都过牌 → 让牌玩家重新 ACTIVE"""
    ...

def test_pass_reactivated_by_duimen_gouji():
    """例外A：玩家0过牌，对门(玩家3)出够级牌 → 玩家0可重新出"""
    rs = init_round(leader=2)
    # 玩家0 (status=PASSED)
    # 玩家3 出 5×10 (够级牌)
    # 验证 玩家0 status=ACTIVE
    ...

def test_pass_reactivated_when_duimen_play_unbeaten():
    """例外B：玩家0过牌，对门牌其他人均未压 → 玩家0 ACTIVE"""
    ...

def test_round_ends_when_all_passed():
    """leader 出牌，其他人都过牌 → 本轮结束，greater_player 拿牌权"""
    ...
```

### test_gouji_env.py

```python
def test_run():
    env = rlcard.make('gouji')
    env.set_agents([RandomAgent(num_actions=1) for _ in range(6)])
    traj, payoffs = env.run()
    assert len(payoffs) == 6
    assert sum(payoffs) == 0  # 3+3 - 3-3 = 0（零和）
```

---

## 验证方法

```bash
# 单独验证牌型逻辑
python -m unittest tests.games.test_gouji_judger -v

# 验证全流程
python -m unittest tests.games.test_gouji_game tests.envs.test_gouji_env -v

# 端到端
python -c "
import rlcard
from rlcard.agents import RandomAgent
env = rlcard.make('gouji')
env.set_agents([RandomAgent(num_actions=1) for _ in range(6)])
traj, payoffs = env.run()
print('payoffs:', payoffs)  # team0=[0,2,4]全1或全-1
"
```

---

## 已与用户确认的关键决策

| 决策点                   | 结论                                           |
| --------------------- | -------------------------------------------- |
| 纯单类王/鹰（如 三大王、三鹰）      | 当作纯 core，core_rank=该王                        |
| 王22 vs 222            | **不能压**（core_rank 必须严格更大）                    |
| 鹰挂的牌之间互相              | 都不可被压（鹰挂享有 PDF 中"大王地位"）                      |
| 混合王挂的覆盖规则             | 每个对方的王都要有对应级别更高（或同级）的王逐位严格管                  |
| 比牌核心条件                | 总张数相等 + 鹰挂不可被压 + 王逐位严格管 + core_rank **严格大于** |
| 贴 2 在比较中的作用           | 只补总张数，不影响 core_rank 与王覆盖                     |
| 纯混合王/鹰组合（如 大王+小王 单独出） | v2 暂不支持，需要时再扩                                |
| 6人座位关系                | 同队交叉落坐（0,2,4 vs 1,3,5）；对门=(i+3)%6；联邦=同队另2人  |
| 买3/买4 决策              | 全自动（按对门 → 联邦 → 上下家优先级，代价用 2→BJ→RJ→免费）       |
| 联邦"送 3"               | 卖家完全免费失去                                     |
| 买 4 范围                | 本阶段只处理抓出逻辑（跨局点贡留 Phase 2）                    |
| 让牌行为                  | 仅为状态标记；任何人出牌后 YIELDED→PASSED；轮回时重新决策         |
| 过牌后例外                 | 本阶段实现：对门出够级牌 / 对门牌无人压 → PASSED→ACTIVE       |
| 状态空间含轮次状态             | 包含：6 玩家本轮状态各 1 维（共 6 维，status/4 归一化）    |
| 动作表示                  | 字符串：`'pass'` / `'yield'` / `cards2str(...)`  |

---

## Phase 2 范围（不在本次实现）

为防止本阶段过载，以下功能列入下一阶段：

- 憋三 / 走科顺序与接风 / 被闷
- 上班 / 抢班 / 大落先发
- 进贡（点贡/烧贡/闷贡/落贡） / 还贡
- 买4 不买的跨局点贡 / 开点判定 / 自然点 / 宣点
- 革命 / 冲点 / 要头 / 无头
- 烧牌 / 解烧 / 反烧 / 烧贡
- 够级牌权限的"无头家"扩展
- 四户乱缠 / 圈三户 / 汇5
