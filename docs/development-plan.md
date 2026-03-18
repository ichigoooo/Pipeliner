# Pipeliner 产品化开发计划（Workflow Studio）

## 目标

保持“设计工作流 → 发布 → 运行 → 调试 → 迭代”闭环稳定可运维，持续降低真实使用中的排障成本与操作复杂度。

## 当前实现概况（2026-03 基线）

已具备：
- Authoring 会话、Claude 生成、发布版本、从版本/attention 发起迭代
- Run 创建、自动驱动、手动 dispatch、attention 介入、artifact/log 预览
- Batch run CSV 模板、顺序执行、批次详情与 workspace 打开
- runs/batches 批量删除、历史保留标记与主列表分组展示
- Claude 连接诊断（base URL、API host、proxy 摘要）与 settings 可视化
- 终端无输出时的排队/慢启动/失败状态解释

当前收口重点：
- 运行时语义一致性（慢启动、真实超时、artifact 缺失优先级）
- 失败路径可观测性（预检失败字段、错误分类、日志留存）
- 文档与 OpenSpec 基线同步（避免实现和规格漂移）

## 阶段规划（滚动）

### 阶段 A：稳定性收口
- 统一 executor/validator/authoring 的诊断口径与错误分类
- 固化慢启动与真实超时语义，并覆盖回归测试
- 保证失败场景保留可追溯元数据

### 阶段 B：运维体验优化
- 强化 runs/batches 的行动优先分组与批量清理体验
- 优化 run detail 的“跟随焦点 / 固定历史轮次”交互
- 持续压缩“页面无输出但实际在运行”带来的误判成本

### 阶段 C：基线治理
- 定期同步 README、Studio 使用文档、OpenSpec 主规格
- 完成已结束 change 的归档，避免需求重复维护
- 将关键验收路径固化为自动化测试

## 验收标准（无 CLI）

1. 用户可在 Studio 完成创建会话、生成草案、发布版本。
2. 用户可在 Studio 启动 run、自动驱动并定位失败原因。
3. 用户可在 attention 完成重试或发起迭代，形成回路。
4. 用户可在 runs/batches 批量清理历史项且不丢失必要追溯信息。
5. 用户可在 settings/terminal 快速识别 Claude 网络与代理配置问题。

## 风险与依赖

风险：
- 外部网络波动导致 Claude 调用失败模式增多
- 运行状态解释口径不一致导致误操作

依赖：
- Claude 命令模板与本地网络/代理环境
- 本地文件系统权限、数据库稳定性与测试覆盖率
