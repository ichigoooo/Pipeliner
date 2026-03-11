## Purpose

TBD

## Requirements

### Requirement: 支持从已发布版本创建迭代会话
系统 SHALL 允许用户基于已发布的 workflow version 创建新的 authoring 会话，并将该版本作为草案基线。

#### Scenario: 从已发布版本开始迭代
- **WHEN** 用户选择某个已发布版本并创建迭代会话
- **THEN** 系统创建新 session，并生成基于该版本的初始草案 revision

### Requirement: 支持从 attention 运行发起迭代
系统 SHALL 允许用户从需要人工介入的运行发起 authoring 会话，并携带 rework brief。

#### Scenario: 从 attention 运行创建会话
- **WHEN** 用户在 attention 运行中选择"发起迭代"
- **THEN** 系统创建新 session，初始草案包含来源版本与 rework brief

### Requirement: 迭代会话保留来源追踪
系统 SHALL 记录迭代会话的来源版本或运行上下文，便于追溯。

#### Scenario: 追踪会话来源
- **WHEN** 用户查看迭代会话详情
- **THEN** 系统显示其来源的 workflow version 或 run 引用
