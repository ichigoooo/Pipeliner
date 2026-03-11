## ADDED Requirements

### Requirement: 可查看 artifact manifest 与存储引用
系统 SHALL 在 Studio 中展示 artifact manifest、storage uri 与关联的 run/node 信息。 
#### Scenario: 查看某个 artifact 详情
- **WHEN** 用户在 run 或 node round 中选择某个 artifact
- **THEN** 系统展示其 manifest、storage uri 与来源信息

### Requirement: 支持 artifact 与日志的只读预览
系统 SHALL 为可预览的 artifact 或日志提供只读预览，并在超出限制时提供路径提示。 
#### Scenario: 预览可读内容
- **WHEN** 用户打开可预览的 artifact 或日志
- **THEN** 系统展示内容预览或在超限时提示下载/路径
