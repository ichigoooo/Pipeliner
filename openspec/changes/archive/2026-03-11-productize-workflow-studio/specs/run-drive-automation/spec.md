## ADDED Requirements

### Requirement: 支持自动驱动运行
系统 SHALL 提供自动驱动运行的能力，按可执行节点顺序调度直到终态或达到步数上限。 
#### Scenario: 自动驱动至终态
- **WHEN** 操作员对某个 run 发起自动驱动请求并设置最大步数
- **THEN** 系统按顺序调度可执行节点，直到 run 进入终态或超过步数上限

### Requirement: 返回驱动结果摘要
系统 SHALL 返回驱动结果摘要，包括 stop_reason 与步骤列表。 
#### Scenario: 获取驱动摘要
- **WHEN** 自动驱动请求完成
- **THEN** 系统返回 stop_reason、执行步骤与最终 run 状态
