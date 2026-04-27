# CLAUDE.md

本文件为在此代码库中使用 Claude Code（claude.ai/code）提供指导。

## 项目概述

RLCard 是一个用于卡牌游戏强化学习（RL）的工具包。它由德州农工大学（Texas A&M）和莱斯大学（Rice University）的 DATA Lab 开发，主要用于研究强化学习在不完全信息博弈中的应用。

**核心功能：**
- **游戏环境**：支持 8 种卡牌游戏
  - Blackjack（二十一点）- 简单，主要用于快速测试
  - Leduc Hold'em - 扑克的简化版本，常用作基准测试
  - Limit Texas Hold'em - 限注德州扑克
  - No-limit Texas Hold'em - 无限注德州扑克
  - Dou Dizhu（斗地主）- 复杂的三人游戏，信息熵最高
  - Mahjong（麻将）- 复杂度最高的游戏之一
  - UNO - 快速卡牌游戏
  - Gin Rummy - 社区贡献
  - Bridge - 四人合作游戏

- **强化学习算法**：
  - DQN（Deep Q-Learning）- 深度Q学习
  - NFSP（Neural Fictitious Self-Play）- 神经虚拟自博弈
  - CFR（Counterfactual Regret Minimization）- 反事实遗憾最小化
  - DMC（Deep Monte-Carlo）- 深度蒙特卡洛

- **预训练模型**：Leduc Hold'em CFR 模型、各游戏的规则模型

- **代理框架**：标准化的 Agent 接口，支持训练和评估模式

## 开发环境设置

### 克隆与安装

```bash
# 克隆仓库
git clone https://github.com/datamllab/rlcard.git
cd rlcard

# 开发模式安装（推荐）
pip install -e .

# 如需使用 PyTorch 算法（可选）
pip install -e ".[torch]"
```

### 目录结构详解

```
rlcard/
├── agents/                          # RL 算法和代理实现
│   ├── dmc_agent/                  # 深度蒙特卡洛代理
│   ├── human_agents/               # 人类交互代理（用于 GUI）
│   ├── agent.py                    # 基础 Agent 类（所有代理的父类）
│   ├── dqn_agent.py               # Deep Q-Network 实现
│   ├── nfsp_agent.py              # Neural Fictitious Self-Play 实现
│   ├── cfr_agent.py               # Counterfactual Regret Minimization
│   └── random_agent.py            # 随机代理（基线）
│
├── envs/                           # 环境包装器，提供统一接口
│   ├── env.py                     # 基础 Env 类和游戏注册机制
│   ├── blackjack.py               # 二十一点环境
│   ├── doudizhu.py                # 斗地主环境
│   ├── leducholdem.py             # Leduc Hold'em 环境
│   ├── limitholdem.py             # 限注德州扑克环境
│   ├── nolimitholdem.py           # 无限注德州扑克环境
│   ├── mahjong.py                 # 麻将环境
│   ├── uno.py                     # UNO 环境
│   ├── gin_rummy.py               # Gin Rummy 环境
│   └── bridge.py                  # Bridge 环境
│
├── games/                          # 核心游戏引擎（不含 RL 相关逻辑）
│   ├── blackjack/
│   │   ├── game.py                # 游戏主类
│   │   ├── dealer.py              # 发牌者
│   │   ├── player.py              # 玩家
│   │   └── utils.py               # 工具函数
│   ├── doudizhu/                  # 斗地主游戏引擎
│   ├── leducholdem/               # Leduc Hold'em 游戏引擎
│   ├── limitholdem/               # 限注德州扑克游戏引擎
│   ├── nolimitholdem/             # 无限注德州扑克游戏引擎
│   ├── mahjong/                   # 麻将游戏引擎
│   ├── uno/                       # UNO 游戏引擎
│   ├── gin_rummy/                 # Gin Rummy 游戏引擎
│   ├── bridge/                    # Bridge 游戏引擎
│   └── __init__.py                # 游戏注册
│
├── models/                        # 预训练模型和规则模型
│   ├── pretrained/               # 预训练模型（如 CFR Leduc Hold'em）
│   ├── leduc_holdem/             # Leduc Hold'em 规则模型
│   ├── doudizhu/                 # 斗地主规则模型
│   └── __init__.py               # 模型注册和加载
│
├── utils/                        # 通用工具函数
│   ├── utils.py                 # 通用工具（排         # 通用工具（排名、花色编码等）
│   ├── logger.py                # 日志记录工具名、花色编码等）
│   ├── logger.py                # 日志记录工具
│   └── *.py                     # 游戏特定的工具
│
├── __init__.py                   # 主入口，导出 make() 函数
└── VERSION                       # 版本号

examples/                         # 示例脚本
├── run_random.py               # 随机代理基准测试
├── run_rl.py                   # DQN 和 NFSP 训练示例
├── run_cfr.py                  # CFR 算法训练示例
├── run_dmc.py                  # Deep Monte-Carlo 训练示例
├── human/                      # 人类交互示例
│   ├── leduc_holdem_human.py  # Leduc Hold'em 人类交互
│   └── blackjack_human.py     # 二十一点人类交互
└── pettingzoo/                # PettingZoo 兼容示例

tests/                          # 单元测试（与 rlcard 结构对应）
├── envs/                      # 环境测试
│   ├── test_blackjack_env.py
│   ├── test_doudizhu_env.py
│   ├── test_leducholdem_env.py
│   └── ...
├── games/                     # 游戏引擎测试
│   ├── test_blackjack_game.py
│   ├── test_doudizhu_game.py
│   └── ...
├── agents/                    # 代理/算法测试
│   ├── test_dqn.py
│   ├── test_cfr.py
│   └── ...
└── models/                    # 模型测试
    └── test_models.py

docs/                          # 详细文档
├── high-level-design.md      # 系统设计文档
├── games.md                   # 各游戏的规则说明
├── algorithms.md              # 算法详解
├── toy-examples.md            # 各种算法示例
├── adding-new-environments.md # 如何添加新游戏
└── developping-algorithms.md  # 如何实现新算法

README.md                       # 英文文档
README.zh-CN.md               # 中文文档
CONTRIBUTING.md               # 贡献指南
setup.py                      # 项目配置文件
```

## 测试指南

RLCard 使用 Python 内置的 `unittest` 框架进行单元测试。

### 运行所有测试

```bash
# 使用 unittest（推荐）
python -m unittest discover -s tests -p "test_*.py"

# 或使用 pytest（如已安装）
pytest tests/
```

### 运行特定模块的测试

```bash
# 测试所有环境
python -m unittest discover -s tests/envs -p "test_*.py"

# 测试特定环境
python -m unittest tests.envs.test_blackjack_env

# 测试所有游戏引擎
python -m unittest discover -s tests/games -p "test_*.py"

# 测试特定游戏
python -m unittest tests.games.test_doudizhu_game

# 测试算法
python -m unittest tests.agents.test_dqn
```

### 运行单个测试类或方法

```bash
# 运行单个测试类
python -m unittest tests.envs.test_blackjack_env.BlackjackEnvTest

# 运行单个测试方法
python -m unittest tests.envs.test_blackjack_env.BlackjackEnvTest.test_reset
```

### 查看测试覆盖率

```bash
# 安装覆盖率工具
pip install coverage

# 运行测试并生成覆盖率报告
coverage run -m unittest discover -s tests -p "test_*.py"
coverage report
coverage html  # 生成 HTML 报告
```

## 核心架构详解

### 三层架构设计

RLCard 遵循严格的三层架构，各层职责明确，相互解耦：

#### 第一层：游戏引擎（Games）
位置：`/rlcard/games/`

**职责**：实现纯粹的游戏逻辑，不涉及 RL 相关概念。

**关键类**：
- `Game`: 一个完整的游戏序列，从初始状态到终止状态
  - 初始化 Dealer 和 Players
  - 控制游戏主循环
  - 调用 Judger 判定结果
  
- `Round`: 游戏的一个阶段（大多数卡牌游戏自然分为多个轮次）
  - 处理单轮的所有逻辑
  - 返回轮次结果供 Game 使用
  
- `Dealer`: 发牌者，管理卡牌
  - 洗牌
  - 向玩家分配卡牌
  
- `Judger`: 判决者，在轮次或游戏结束时做出重要决定
  - 判定获胜者
  - 计算收益（payoffs）
  
- `Player`: 玩家角色，持有卡牌和状态
  - 存储私有信息（手牌）
  - 接收游戏状态和合法动作列表

**特点**：
- 完全与 RL 解耦
- 可独立运行和测试
- 纯 Python 实现，无依赖

**示例（Blackjack）**：
```python
# games/blackjack/game.py
class Game:
    def __init__(self, seed=None):
        self.dealer = Dealer(seed)
        self.player = Player()
    
    def step(self, action):
        # 执行单步游戏逻辑
        # 返回游戏是否结束
        pass
    
    def get_payoffs(self):
        # 使用 Judger 计算最终收益
        pass
```

#### 第二层：环境包装（Environments）
位置：`/rlcard/envs/`

**职责**：为 RL 提供标准化接口，将游戏逻辑转化为 RL 友好的格式。

**关键方法**：

*简单接口（推荐用于标准 RL 流程）*：
```python
env = rlcard.make('blackjack')
env.set_agents([agent1, agent2])
trajectories, payoffs = env.run(is_training=True)
```

- `set_agents(agents)`: 设置将参与游戏的代理列表，长度必须等于游戏玩家数
- `run(is_training=False)`: 运行一个完整游戏并返回轨迹和收益
  - 若 `is_training=True`，调用 `agent.step(state)` 进行训练
  - 若 `is_training=False`，调用 `agent.eval_step(state)` 进行评估
  - 返回 `(trajectories, payoffs)`：
    - `trajectories`: 格式为 `[[(state0, action0, reward0), ...], [...]]`，按玩家组织
    - `payoffs`: 每个玩家的最终收益列表

*高级接口（用于自定义控制和算法开发）*：
```python
env = rlcard.make('blackjack', config={...})
state, player_id = env.reset()  # 初始化游戏

while not env.is_over():
    legal_actions = state['legal_actions']
    action = agent.select_action(legal_actions)
    state, player_id = env.step(action)

payoffs = env.get_payoffs()  # 获取最终收益
```

- `reset()`: 初始化游戏，返回 `(state, player_id)`
- `step(action, raw_action=False)`: 执行一步
  - `action`: 动作索引或原始动作（如果 `raw_action=True`）
  - 返回 `(state, player_id)`
- `step_back()`: 回退一步（需在 `make()` 时设置 `allow_step_back=True`）
  - 用于 CFR 等需要遍历游戏树的算法
- `is_over()`: 检查游戏是否结束
- `get_player_id()`: 获取当前玩家 ID
- `get_state(player_id)`: 获取特定玩家的状态
- `get_payoffs()`: 获取所有玩家的最终收益
- `get_perfect_information()`: 获取完全信息（仅某些游戏支持）

**状态格式（重要）**：
所有状态都是 Python 字典，包含：
```python
state = {
    'obs': ...,                    # 处理后的观察值（格式因游戏而异）
    'legal_actions': [0, 1, 2],   # 合法动作的索引列表（核心信息）
    'raw_obs': ...,               # 原始观察值（用于调试）
    'raw_legal_actions': [...]    # 原始动作表示（如卡牌或字符串）
}
```

**环境配置示例**：
```python
# 创建带配置的环境
config = {
    'seed': 42,              # 游戏随机种子
    'allow_step_back': True, # 允许回退（用于 CFR）
    'game_num_players': 4    # 游戏特定配置（如 Blackjack 的玩家数）
}
env = rlcard.make('blackjack', config=config)
```

**支持的环境列表**（在 `rlcard/envs/env.py` 的 `SUPPORTED_ENVS` 中）：
- `blackjack`
- `leduc-holdem`
- `limit-holdem`
- `no-limit-holdem`
- `doudizhu`
- `mahjong`
- `uno`
- `gin-rummy`
- `bridge`

#### 第三层：代理（Agents）
位置：`/rlcard/agents/`

**职责**：实现具体的 RL 算法或策略。代理是环境无关的，只通过 `state` 字典与环境交互。

**基础 Agent 类** (`agent.py`)：
```python
class Agent:
    def step(self, state):
        """训练阶段调用，可更新内部模型"""
        pass
    
    def eval_step(self, state):
        """评估阶段调用，不更新模型"""
        pass
    
    def feed_trajectory(self, trajectory):
        """可选：接收完整轨迹用于 off-policy 学习"""
        pass
```

**关键约束**：
- 代理只能看到 `state['obs']` 和 `state['legal_actions']`
- 代理不能访问对手的私有信息（卡牌等）
- 代理必须从合法动作列表中选择
- 代理内部可维护任意状态或模型（神经网络、表格等）

**内置算法**：

1. **DQN** (`dqn_agent.py`)
   - 深度 Q 学习，适合较小状态空间
   - 学习状态-动作价值函数
   - 可选 PyTorch 后端

2. **NFSP** (`nfsp_agent.py`)
   - 神经虚拟自博弈
   - 同时训练监督学习和强化学习组件
   - 用于自博弈场景

3. **CFR** (`cfr_agent.py`)
   - 反事实遗憾最小化
   - 需要 `allow_step_back=True`
   - 最适合不完全信息博弈

4. **DMC** (`dmc_agent/`)
   - 深度蒙特卡洛
   - 强大的 Dou Dizhu 算法
   - 使用神经网络辅助蒙特卡洛搜索

5. **RandomAgent** (`random_agent.py`)
   - 从合法动作中随机选择
   - 用于基准测试和调试

**代理使用示例**：
```python
from rlcard.agents import DQNAgent, CFRAgent, RandomAgent

# 创建代理
dqn_agent = DQNAgent(
    num_actions=env.num_actions,
    state_shape=env.state_shape,
    hidden_layers_sizes=[128, 128]
)

cfr_agent = CFRAgent(num_actions=env.num_actions)

random_agent = RandomAgent(num_actions=env.num_actions)

# 设置到环境
env.set_agents([dqn_agent, random_agent])

# 训练
for episode in range(1000):
    trajectories, payoffs = env.run(is_training=True)
    print(f"Episode {episode}, Payoffs: {payoffs}")

# 评估
trajectories, payoffs = env.run(is_training=False)
```

### 信息流程图

```
用户代码
    |
    v
rlcard.make('game_name')  → 创建 Env 实例
    |
    v
env.set_agents([agent1, agent2])  → 注册代理
    |
    v
env.run(is_training=True)  → 执行游戏循环
    |
    +──→ env.reset()  → Game 初始化
    |
    +──→ for each step:
    |      env.step(action)  → Game.step()
    |      ├─ 更新游戏状态
    |      ├─ 返回新状态给 Agent
    |      └─ Agent 做出决策
    |
    +──→ env.get_payoffs()  → Judger 计算收益
    |
    v
返回 (trajectories, payoffs) 给用户
```

## 收益和奖励系统

**重要概念区分**：
- **收益（Payoff）**：游戏结束时获得的最终值，由 Judger 在游戏结束时计算一次
- **奖励（Reward）**：轨迹中每一步的立即反馈，在轨迹生成阶段计算

**收益类型**：
- 零和游戏：一个玩家的收益 = 其他玩家收益的负和（Leduc Hold'em、Dou Dizhu 等）
- 常和游戏：总收益固定（Blackjack 通常为 ±1）

**轨迹格式示例**：
```python
trajectories = [
    [  # Player 0 的轨迹
        (state0, action0, reward0),  # step 1
        (state1, action1, reward1),  # step 2
        ...
    ],
    [  # Player 1 的轨迹
        (state0, action0, reward0),
        ...
    ]
]

payoffs = [1.0, -1.0]  # Player 0 赢，Player 1 输
```

## 添加新游戏：完整指南

### 第一步：创建游戏引擎

创建 `/rlcard/games/your_game/` 目录：

```python
# games/your_game/game.py
class Game:
    def __init__(self, seed=None):
        self.seed = seed
        self.dealer = Dealer(seed)
        self.players = [Player(i) for i in range(self.num_players)]
        self.judger = Judger()
        self.current_player_id = 0
        self.round = 0
    
    def step(self, action):
        """执行一步，返回游戏是否结束"""
        self.round_obj.proceed_round(self.players[self.current_player_id], action)
        self.current_player_id = (self.current_player_id + 1) % len(self.players)
        return self.is_over()
    
    def is_over(self):
        """检查游戏是否结束"""
        pass
    
    def get_payoffs(self):
        """获取最终收益，返回列表"""
        return self.judger.judge_game(self.players, ...)

# games/your_game/dealer.py
class Dealer:
    def __init__(self, seed=None):
        self.deck = ...
        self.seed = seed
    
    def shuffle(self):
        """洗牌"""
        pass
    
    def deal_cards(self, players):
        """向玩家分配卡牌"""
        pass

# games/your_game/player.py
class Player:
    def __init__(self, player_id):
        self.player_id = player_id
        self.hand = []  # 手中的卡牌
    
    def receive_cards(self, cards):
        self.hand.extend(cards)

# games/your_game/judger.py
class Judger:
    def judge_game(self, players, ...):
        """判定游戏结果"""
        payoffs = [0] * len(players)
        # 计算每个玩家的收益
        return payoffs

# games/your_game/__init__.py
from .game import Game
from .dealer import Dealer
from .player import Player
from .judger import Judger

__all__ = ['Game', 'Dealer', 'Player', 'Judger']
```

### 第二步：创建环境包装

创建 `/rlcard/envs/your_game_env.py`：

```python
from rlcard.envs.env import Env
from rlcard.games.your_game import Game
import numpy as np

class YourGameEnv(Env):
    """Your Game 的环境包装"""
    
    # 游戏特定的配置项（所有键必须以 game_ 开头）
    DEFAULT_GAME_CONFIG = {
        'game_option1': value1,
        'game_option2': value2,
    }
    
    def __init__(self, config=None):
        self.config = config or {}
        self.game = Game(
            seed=self.config.get('seed'),
            option1=self.config.get('game_option1'),
        )
        
        # 定义 RL 相关属性
        self.num_actions = 10  # 游戏中可能的动作数量
        self.num_players = 2   # 玩家数量
        self.state_shape = [[20]]  # 观察向量的形状，每个玩家一个
        self.action_shape = [None]  # 动作特征形状（卡牌游戏通常为 None）
        
        self.player_ids = list(range(self.num_players))
        self.state = None
    
    def _get_obs(self, player_id):
        """从游戏状态生成观察向量
        
        返回可以被代理处理的观察（通常是 numpy 数组）
        """
        # 将游戏特定的信息转化为通用的观察格式
        hand = self.game.players[player_id].hand
        obs = np.zeros(20, dtype=np.int32)
        for card in hand:
            obs[card_to_index(card)] = 1
        return obs
    
    def _get_legal_actions(self, player_id):
        """获取当前玩家的合法动作列表"""
        legal_actions = []
        for action in range(self.num_actions):
            if self._is_action_valid(action, player_id):
                legal_actions.append(action)
        return legal_actions if legal_actions else [0]  # 至少有一个默认动作
    
    def _is_action_valid(self, action, player_id):
        """检查动作是否有效"""
        # 根据游戏规则检查动作合法性
        pass
    
    def reset(self):
        """重置游戏"""
        self.game = Game(seed=self.config.get('seed'))
        player_id = self.game.current_player_id
        self.state = {
            'obs': self._get_obs(player_id),
            'legal_actions': self._get_legal_actions(player_id),
            'raw_obs': str(self.game.players[player_id].hand),  # 调试用
            'raw_legal_actions': [action_to_string(a) for a in self._get_legal_actions(player_id)],
        }
        return self.state, player_id
    
    def step(self, action, raw_action=False):
        """执行一步动作"""
        if raw_action:
            # 从原始动作转化为索引
            action = raw_action_to_index(action)
        
        # 执行游戏逻辑
        self.game.step(action)
        
        player_id = self.game.current_player_id
        self.state = {
            'obs': self._get_obs(player_id),
            'legal_actions': self._get_legal_actions(player_id),
            'raw_obs': str(self.game.players[player_id].hand),
            'raw_legal_actions': [...],
        }
        return self.state, player_id
    
    def is_over(self):
        """游戏是否结束"""
        return self.game.is_over()
    
    def get_payoffs(self):
        """获取最终收益"""
        return self.game.get_payoffs()
    
    def get_perfect_information(self):
        """获取完全信息（可选，用于调试）"""
        info = {}
        for player_id in range(self.num_players):
            info[f'player_{player_id}_hand'] = str(self.game.players[player_id].hand)
        return info
```

### 第三步：注册环境

编辑 `/rlcard/envs/env.py`，在 `SUPPORTED_ENVS` 字典中添加：

```python
# 在 envs/env.py 的 SUPPORTED_ENVS 字典中
SUPPORTED_ENVS = {
    ...
    'your-game': YourGameEnv,
}
```

还要在 `/rlcard/envs/__init__.py` 中导出：

```python
from .your_game_env import YourGameEnv

__all__ = ['YourGameEnv', ...]
```

### 第四步：编写测试

创建 `/tests/envs/test_your_game_env.py`：

```python
import unittest
from rlcard.envs import YourGameEnv
from rlcard.agents import RandomAgent

class YourGameEnvTest(unittest.TestCase):
    def setUp(self):
        self.env = YourGameEnv()
    
    def test_reset(self):
        """测试环境重置"""
        state, player_id = self.env.reset()
        self.assertIn('obs', state)
        self.assertIn('legal_actions', state)
        self.assertIsInstance(player_id, int)
    
    def test_step(self):
        """测试环境步进"""
        self.env.reset()
        action = self.env.state['legal_actions'][0]
        state, player_id = self.env.step(action)
        self.assertIn('obs', state)
    
    def test_run_with_agents(self):
        """测试完整游戏运行"""
        self.env.set_agents([
            RandomAgent(num_actions=self.env.num_actions),
            RandomAgent(num_actions=self.env.num_actions),
        ])
        trajectories, payoffs = self.env.run()
        self.assertEqual(len(trajectories), 2)
        self.assertEqual(len(payoffs), 2)

if __name__ == '__main__':
    unittest.main()
```

创建 `/tests/games/test_your_game_game.py`：

```python
import unittest
from rlcard.games.your_game import Game

class YourGameTest(unittest.TestCase):
    def setUp(self):
        self.game = Game()
    
    def test_initialization(self):
        """测试游戏初始化"""
        self.assertEqual(len(self.game.players), 2)
        self.assertFalse(self.game.is_over())
    
    def test_step(self):
        """测试游戏步进"""
        action = 0
        game_over = self.game.step(action)
        self.assertIsInstance(game_over, bool)
    
    def test_payoffs(self):
        """测试收益计算"""
        while not self.game.is_over():
            self.game.step(0)
        payoffs = self.game.get_payoffs()
        self.assertEqual(len(payoffs), 2)
        self.assertAlmostEqual(sum(payoffs), 0)  # 零和游戏

if __name__ == '__main__':
    unittest.main()
```

## 添加新代理/算法：完整指南

### 第一步：选择基类

所有代理都继承自 `Agent` 基类：

```python
# rlcard/agents/agent.py
class Agent:
    def step(self, state):
        """训练阶段调用，返回动作索引"""
        raise NotImplementedError
    
    def eval_step(self, state):
        """评估阶段调用，返回动作索引"""
        raise NotImplementedError
    
    def feed_trajectory(self, trajectory):
        """可选：接收完整轨迹（用于 off-policy 学习）"""
        pass
```

### 第二步：实现代理

创建 `/rlcard/agents/your_algorithm.py`：

```python
import numpy as np
from rlcard.agents.agent import Agent

class YourAlgorithm(Agent):
    """Your Algorithm 的实现"""
    
    def __init__(self, num_actions, state_shape=None, learning_rate=0.01):
        """
        参数说明：
        - num_actions: 动作空间大小
        - state_shape: 状态形状（可选，用于神经网络）
        - learning_rate: 学习率
        """
        self.num_actions = num_actions
        self.state_shape = state_shape
        self.learning_rate = learning_rate
        
        # 初始化你的模型/表格
        self.q_table = np.zeros((1000, num_actions))  # 简单 Q-learning 例子
    
    def step(self, state):
        """训练阶段：选择动作并更新模型"""
        obs = state['obs']  # 观察值
        legal_actions = state['legal_actions']  # 合法动作
        
        # 使用 epsilon-greedy 策略
        if np.random.random() < self.epsilon:
            action = legal_actions[np.random.randint(len(legal_actions))]
        else:
            state_index = self._obs_to_index(obs)
            action = legal_actions[np.argmax(self.q_table[state_index, legal_actions])]
        
        # 存储状态用于后续更新（off-policy）
        self.last_state = state
        self.last_action = action
        
        return action
    
    def eval_step(self, state):
        """评估阶段：仅选择动作，不更新模型"""
        obs = state['obs']
        legal_actions = state['legal_actions']
        
        # 贪心策略
        state_index = self._obs_to_index(obs)
        action = legal_actions[np.argmax(self.q_table[state_index, legal_actions])]
        
        return action
    
    def feed_trajectory(self, trajectory):
        """使用完整轨迹进行学习"""
        # trajectory = [(state0, action0, reward0), (state1, action1, reward1), ...]
        
        for i in range(len(trajectory) - 1):
            state, action, reward = trajectory[i]
            next_state, _, _ = trajectory[i + 1]
            
            state_index = self._obs_to_index(state['obs'])
            next_state_index = self._obs_to_index(next_state['obs'])
            
            # Q-learning 更新
            next_q_max = np.max(self.q_table[next_state_index])
            self.q_table[state_index, action] += self.learning_rate * (
                reward + 0.99 * next_q_max - self.q_table[state_index, action]
            )
    
    def _obs_to_index(self, obs):
        """将观察转化为表格索引（仅用于表格方法）"""
        # 简单实现，实际应根据观察空间调整
        return int(np.sum(obs)) % 1000
```

### 第三步：集成代理

编辑 `/rlcard/agents/__init__.py`：

```python
from .your_algorithm import YourAlgorithm

__all__ = ['YourAlgorithm', ...]
```

### 第四步：编写测试

创建 `/tests/agents/test_your_algorithm.py`：

```python
import unittest
from rlcard.agents import YourAlgorithm
from rlcard.envs import make

class YourAlgorithmTest(unittest.TestCase):
    def setUp(self):
        self.agent = YourAlgorithm(num_actions=2)
        self.env = make('blackjack')
    
    def test_step(self):
        """测试代理 step 方法"""
        state, _ = self.env.reset()
        action = self.agent.step(state)
        self.assertIn(action, state['legal_actions'])
    
    def test_eval_step(self):
        """测试代理 eval_step 方法"""
        state, _ = self.env.reset()
        action = self.agent.eval_step(state)
        self.assertIn(action, state['legal_actions'])
    
    def test_training(self):
        """测试完整训练流程"""
        self.env.set_agents([self.agent, RandomAgent(num_actions=self.env.num_actions)])
        
        for _ in range(10):
            trajectories, payoffs = self.env.run(is_training=True)
            for trajectory in trajectories:
                self.agent.feed_trajectory(trajectory)

if __name__ == '__main__':
    unittest.main()
```

## 游戏配置系统

RLCard 支持游戏特定的配置。所有配置键必须以 `game_` 开头，以区别于系统配置。

### 示例：Blackjack 多人配置

```python
# envs/blackjack.py
DEFAULT_GAME_CONFIG = {
    'game_num_players': 1,  # 玩家数量（1-10）
}

class BlackjackEnv(Env):
    def __init__(self, config=None):
        self.config = config or {}
        num_players = self.config.get('game_num_players', 1)
        self.game = Game(num_players=num_players)
        ...
```

### 使用配置

```python
# 创建标准的单人 Blackjack
env = rlcard.make('blackjack')

# 创建三人 Blackjack
env = rlcard.make('blackjack', config={'game_num_players': 3})

# 设置种子和配置
env = rlcard.make('blackjack', config={
    'seed': 42,
    'game_num_players': 2,
})
```

## 关键文件速查

| 文件 | 用途 |
|------|------|
| `rlcard/__init__.py` | 主入口，`make()` 函数定义，版本号 |
| `rlcard/envs/env.py` | 基础 `Env` 类、游戏注册机制、通用接口 |
| `rlcard/agents/agent.py` | 基础 `Agent` 类、接口定义 |
| `rlcard/utils/utils.py` | 跨游戏的通用工具（排名、花色编码等） |
| `rlcard/games/game_name/game.py` | 特定游戏的核心逻辑 |
| `rlcard/envs/game_name.py` | 特定游戏的环境包装 |
| 各游戏的 `utils.py` | 游戏特定的工具函数 |

## 运行示例

### 基础示例

```bash
# 使用随机代理运行 Blackjack（快速测试）
python examples/run_random.py --env blackjack --num_games 100

# 训练 DQN 代理在 Blackjack
python examples/run_rl.py --env blackjack --algorithm dqn --num_episodes 1000

# 训练 CFR 代理在 Leduc Hold'em（最推荐用于不完全信息）
python examples/run_cfr.py --env leduc-holdem --iterations 100000

# 训练 Deep Monte-Carlo 代理在 Dou Dizhu
python examples/run_dmc.py
```

### 自定义脚本示例

```python
import rlcard
from rlcard.agents import DQNAgent, RandomAgent

# 创建环境
env = rlcard.make('blackjack')

# 创建代理
dqn_agent = DQNAgent(
    num_actions=env.num_actions,
    state_shape=env.state_shape,
)
random_agent = RandomAgent(num_actions=env.num_actions)

# 设置代理
env.set_agents([dqn_agent, random_agent])

# 训练
for episode in range(100):
    trajectories, payoffs = env.run(is_training=True)
    print(f"Episode {episode}: Payoffs = {payoffs}")

# 评估
print("\n=== Evaluation ===")
total_payoff = 0
for _ in range(100):
    trajectories, payoffs = env.run(is_training=False)
    total_payoff += payoffs[0]

print(f"Average payoff: {total_payoff / 100}")
```

## 常见开发任务

### 修改游戏规则
1. 编辑相应的 `games/game_name/game.py` 或其他类
2. 运行 `tests/games/test_game_name_game.py` 验证游戏逻辑
3. 运行 `tests/envs/test_game_name_env.py` 验证环境集成

### 调试代理行为
使用高级环境接口进行单步调试：

```python
env = rlcard.make('blackjack', config={'seed': 42})
state, player_id = env.reset()

print(f"Initial state: {state}")
print(f"Current player: {player_id}")

for step in range(10):
    if env.is_over():
        break
    
    action = state['legal_actions'][0]  # 选择第一个合法动作
    print(f"\nStep {step}: Player {player_id} takes action {action}")
    
    state, player_id = env.step(action)
    print(f"New state: {state['obs']}")
    print(f"Next player: {player_id}")

print(f"\nGame over. Payoffs: {env.get_payoffs()}")
```

### 分析游戏树（仅限支持 step_back 的游戏）
```python
env = rlcard.make('leduc-holdem', config={'allow_step_back': True})
state, player_id = env.reset()

# 执行若干步
for _ in range(5):
    if not env.is_over():
        env.step(state['legal_actions'][0])

# 回退
env.step_back()
print(f"Stepped back to state: {env.get_state(env.get_player_id())}")
```

## 重要注意事项

### 不完全信息原则
RLCard 严格遵循不完全信息：
- 代理**不能**访问对手的卡牌
- 代理**只能**看到 `state['obs']` 和 `state['legal_actions']`
- 这是区别于其他游戏框架的关键特性

### 确定性和可重现性
```python
# 使用种子确保结果可重现
env = rlcard.make('blackjack', config={'seed': 42})
env.reset()  # 每次都会生成相同的初始状态
```

### PyTorch 依赖
- 默认安装不包括 PyTorch，DQN 等会自动使用 NumPy 版本
- 若需 PyTorch：`pip install -e ".[torch]"`
- PyTorch 版本在 `rlcard/agents/dqn_agent.py` 中用条件导入

### 性能优化
- 使用 `run_random.py` 进行性能基准测试
- Dou Dizhu 和 Mahjong 计算复杂度高，考虑使用 `allow_step_back=False` 加速
- 大规模训练时使用 PyTorch 后端（GPU 支持）

### 贡献指南
- 新游戏：联系 daochen.zha@tamu.edu 讨论设计
- 新算法：遵循 Agent 接口，添加完整测试
- 规则修正：优先级最高，欢迎 PR
- 代码风格：遵循 PEP 8，运行 `black` 格式化
