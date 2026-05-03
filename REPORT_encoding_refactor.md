# 够级牌模型编码重构报告

**日期**: 2026-05-03  
**改动范围**: `rlcard/games/gouji/` + `rlcard/envs/gouji.py` + `tests/games/test_gouji_*.py`

---

## 目标

将够级牌模型从 `Card(suit, rank)` 对象清洗为纯 rank 字符串，建立 `string ↔ Play ↔ tensor` 编码管线。

## 改动清单（8 个核心文件）

| 文件 | 改动 |
|------|------|
| `judger.py` | Play 去 `is_pass` 字段→`is_pass()` 方法；新增 `to_array()`/`from_array()` 6维张量互转；`parse_play` 改为接收 rank 字符串列表；`is_valid_play`/`playable_cards_from_hand` 改为接收 16 维 hand 向量；`can_beat` 王比较修复 `<` 替代 `<=` |
| `player.py` | **hand** 从 `list[Card]` 改为 `np.ndarray(16,int32)` 计数向量；`remove_cards` 改为按 Play 直接索引扣减 O(1)；新增 `add_rank(rank, count)` |
| `dealer.py` | 去掉 `from rlcard.games.base import Card`；牌组直接用 rank 字符串列表；`deal` 改为给 hand 向量递增计数 |
| `buy_phase.py` | `execute_buy`/`_trade` 改为操作 16 维向量索引 |
| `game.py` | `step` 用 `str_to_play()` 替代 `_pick_cards_for_action`+`parse_play`；`_played_arrays` 更新简化；`get_state` 直接返回 hand 向量 |
| `utils.py` | 去掉 `SUIT_STR`、`TOTAL_CARDS`、`get_rank_index`、`is_attach_card`、`is_wang`、`hand_to_rank_array`、`cards2str`；新增 `str_to_play`、`play_to_str`、`play_to_ranks`、`ranks_to_str` |
| `envs/gouji.py` | `_extract_state` 手牌归一化改为直接 `hand[i] / RANK_MAX_COUNT` |
| `__init__.py` | 导出符号同步更新 |

## 数据流

```
发牌: dealer._build_deck() → ['7','7',...,'BJ'] → shuffle → deal → player.hand[idx]++
出牌: action_str → str_to_play() → Play → player.remove_cards(play)
编码: Play.to_array() → 6维浮点; player.hand → 16维计数 → 归一化 → RL输入
```

## 编码代码布局

```
utils.py
├── 常量: RANK_STR, RANK_INDEX, RANK_MAX_COUNT, NUM_RANKS
├── 座位: team_id, is_lianbang, is_duimen, duimen_of, buyer_priority_sellers
├── str ↔ list: str2ranks, ranks_to_str
├── str ↔ Play: str_to_play, play_to_str              (新增)
└── Play → list: play_to_ranks                         (新增)

judger.py
├── Play 数据类: core_rank, core_count, attach_2, attach_BJ, attach_RJ, attach_Y
│   ├── to_array(), from_array()                       (新增)
│   ├── is_pass(), total(), wang_list_desc(), attach_wangs_total()
│   └── is_gouji(), is_pure_gouji()
├── PASS_PLAY
└── GoujiJudger (静态方法集)
    ├── parse_play(ranks) → Play
    ├── can_beat(ranks, play) → bool
    ├── playable_cards_from_hand(hand_16d, ...) → set[str]
    ├── is_valid_play / is_valid_play_with_constraints
    └── judge_game / judge_payoffs

player.py
└── GoujiPlayer
    ├── hand: np.ndarray(16,) int32
    ├── played_history: np.ndarray(16,) int32
    ├── remove_cards(play: Play)
    └── add_rank(rank: str, count: int)
```

## 测试结果

- **judger 测试**: 31/31 通过 (含新增的 PlayArray 往返测试)
- **buy_phase 测试**: 7/7 通过
- **round 测试**: 5/7 通过 (2 个失败为预存例外B逻辑缺陷)
- **编码管线冒烟**: str↔Play 往返正确, to_array/from_array 互转正确

## 未涉及的预存问题

`round.py` 的例外 B 在 `_advance_turn` 中每次都会全量扫描触发，导致玩家被过早重新激活。需要后续修复。
