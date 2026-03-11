## ADDED Requirements

### Requirement: Authoring 会话支持 Claude Code 生成草案
系统 SHALL 允许用户在 authoring 会话中请求 Claude Code 生成新的草案版本，并将结果保存为新的 revision。 
#### Scenario: 生成新的草案 revision
- **WHEN** 用户提交包含 intent brief、instruction 与当前草案 spec 的生成请求
- **THEN** 系统创建新的 draft revision，并返回同步派生的 workflow view、graph 与 lint 报告

### Requirement: 生成失败不覆盖现有草案
系统 SHALL 在生成失败时保留最新草案不变，并记录失败原因以便排查。 
#### Scenario: Claude Code 调用失败
- **WHEN** 生成请求失败或返回不可解析的 spec
- **THEN** 系统保留最新 draft revision 不变，并返回可诊断的错误信息

### Requirement: 生成过程可审计
系统 SHALL 记录每次生成请求的元信息，便于追踪与审计。 
#### Scenario: 记录生成元信息
- **WHEN** 一次生成请求完成（成功或失败）
- **THEN** 系统记录生成时间、耗时与关联 revision 作为审计信息
