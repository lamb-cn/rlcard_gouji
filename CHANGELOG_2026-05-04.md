# 2026-05-04

- 牌模型去花色：Card(suit,rank) → rank字符串，手牌改为16维计数向量
- Play: 去is_pass字段，加to_array()/from_array() 6维张量互转
- 新增str_to_play/play_to_str双向转换，打通string↔Play↔tensor管线
- can_beat重构：二杀一(2同级王→1)、三杀一(3低→1高)，非王牌恰好压完
- buy_phase合并到dealer，买牌改为全员对家→全员联邦的轮次优先
