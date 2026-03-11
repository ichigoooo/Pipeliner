# Pipeliner 产品化开发计划（Workflow Studio）

## 目标

将 Workflow Studio 前端与后端能力打通，完整支持“设计工作流 → 发布 → 运行 → 调试 → 迭代”闭环，并确保与现有设计文档一致。+
## 当前实现概况（基线）

已具备：
- workflow spec 注册与校验
- runtime 状态机、callback 协议与 artifact manifest
- 运行调度器（CLI 侧 run drive）
- attention 队列、停止与重试
- Studio 多视图（cards / graph / spec / lint）
- run 调试工作台、设置溯源面板

未完整实现：
- Authoring 阶段的对话式生成（Claude Code 接入）
- 运行自动驱动的前端入口
- 由运行反馈驱动的迭代闭环
- 产物与日志可读性提升

## 里程碑与工作项

### 阶段 0：需求矩阵与验收定义
- 输出需求矩阵（设计文档 → 现状 → 缺口）
- 定义验收用例（无 CLI 场景）

### 阶段 1：Authoring Claude 接入（核心缺口）

后端：
- 增加 Authoring Agent 服务：输入 intent brief + instruction + spec，输出新 spec
- 通过命令模板接入 Claude（与 executor/validator 风格一致）
- 新增 API：`POST /api/authoring/sessions/{id}/generate` 或 `continue` 支持 `use_agent=true`
- 记录调用日志与失败原因

前端：
- 新增“生成下一版”入口，区分“仅保存”与“调用 Claude”
- 显示生成进度、耗时、错误
- 增加草案差异视图（diff）

### 阶段 2：创作闭环与迭代
- 支持从已发布版本创建 authoring session
- 支持从 attention 运行生成草案（携带 rework brief）
- lint 阻塞错误定位到具体字段

### 阶段 3：运行自动调度（Run Drive）
- 新增 API：`POST /api/runs/{id}/drive`（复用 RunDriver）
- 前端 Run 页面提供“一键驱动/继续驱动”入口
- 保留单节点手动 dispatch

### 阶段 4：产物与日志可读性
- Artifact 详情页支持 manifest + 可预览
- 日志引用可只读查看（本地文件）
- 运行详情补充 callback → artifact 链路

### 阶段 5：产品化收尾
- 空状态与错误态统一
- 设置面板补充“来源解释”
- 端到端无 CLI 流程验证

## 验收标准（无 CLI）

1. 在 Studio 创建会话并生成草案
2. 通过 lint 后发布 workflow version
3. 在 Studio 启动 run 并自动驱动至终态
4. 在 attention 中处理阻塞与重试
5. 从运行反馈发起新一轮迭代并再次发布

## 风险与依赖

风险：
- Claude 调用失败导致草案不稳定
- diff 与 lint 信息过载影响可用性

依赖：
- Claude 命令模板与本地可执行环境
- 持久化与 workspace 目录权限
