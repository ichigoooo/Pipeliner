## Purpose

TBD

## Requirements

### Requirement: Claude 调用入口提供可展开终端视图
系统 SHALL 在所有触发 Claude Code 调用的 UI 入口提供可展开的终端视图，默认折叠，仅在用户主动展开时显示。
#### Scenario: 展开终端查看输出
- **WHEN** 用户在任一 Claude Code 调用入口触发生成并展开终端面板
- **THEN** 系统显示该次调用的终端输出流与当前状态

### Requirement: 终端输出实时追加并可回放
系统 SHALL 以时间顺序实时追加 Claude Code 调用输出，并在调用结束后保留完整输出以便回看与排查。
#### Scenario: 调用完成后回看输出
- **WHEN** 一次 Claude Code 调用完成（成功或失败）
- **THEN** 用户仍可在终端面板中查看完整输出内容与最终状态

### Requirement: 终端只读且输出与 CLI 一致
系统 SHALL 以只读方式展示 Claude Code 调用的终端输出，内容与 CLI 调用时的 stdout/stderr 与流程输出保持一致。
#### Scenario: 只读终端展示
- **WHEN** 用户查看终端面板
- **THEN** 面板不提供任何输入或控制操作，仅展示输出内容

### Requirement: 思维链/流程输出可用时展示
系统 SHALL 在上游已记录且允许展示时，将 Claude Code 的思维链或流程输出作为终端输出的一部分展示。
#### Scenario: 上游提供思维链输出
- **WHEN** Claude Code 调用返回可展示的思维链或流程输出片段
- **THEN** 终端面板将其按顺序展示在输出流中
