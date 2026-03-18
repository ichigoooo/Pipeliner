## MODIFIED Requirements

### Requirement: 生成失败不覆盖现有草案
系统 SHALL 在生成失败时保留最新草案不变，并记录失败原因以便排查；当失败由网络、代理、域名解析、连接预检或命令模板问题引起时，系统 SHALL 返回可操作的诊断信息，而不是仅返回泛化失败。

#### Scenario: Claude Code 调用失败
- **WHEN** 生成请求失败或返回不可解析的 spec
- **THEN** 系统保留最新 draft revision 不变，并返回可诊断的错误信息

#### Scenario: 连接预检失败时返回可操作提示
- **WHEN** authoring agent 在真正启动 Claude 调用前就检测到域名解析或基础连接问题
- **THEN** 系统保留现有草案不变，并返回带有具体排查方向的错误信息，例如 host、代理或网络问题
