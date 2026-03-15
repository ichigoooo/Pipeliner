## Context

现有运行入口围绕单次 `run` 设计，适合交互式调试，但不适合对同一工作流版本批量提交多组 workflow inputs。当前已经具备：

- 工作流输入定义与结构化表单渲染
- run 创建、自动驱动、运行详情与 workspace 打开能力

缺失的是面向“多行输入”的上层编排与结果聚合。这个 change 将 batch run 设计为附着在工作流版本之上的一层轻量 orchestration，而不是修改底层单个 run 的语义。

## Goals / Non-Goals

**Goals:**

- 为给定工作流版本生成可直接填写的 CSV 模板。
- 接受 CSV 上传并创建 batch run / batch run items。
- 对合法输入串行启动 run，并复用现有 auto-drive 能力完成执行。
- 在 Studio 中提供批次详情页，展示聚合进度、逐行状态、run 链接和打开 workspace 动作。

**Non-Goals:**

- 并行执行 batch items。
- 在 batch 上传时引入新的 artifact 存储协议或文件上传机制。
- 为 batch run 引入独立于现有 run driver 之外的复杂调度系统。

## Decisions

### 1. Batch run 作为 run orchestration 的上层记录存在

批量执行不是新的 runtime primitive，而是对一组普通 run 的顺序驱动。因此后端仅新增 `batch_runs` / `batch_run_items` 记录批次元数据和每一行输入，而实际执行仍复用既有 run 创建与 auto-drive。

这样可以保持：

- 单个 run 的状态机与调试入口不变
- batch 只是 orchestration 和聚合层
- 失败 item 仍可通过对应 run workspace 独立排查

### 2. CSV 模板直接使用 workflow inputs 作为表头

模板的目标是最小惊讶原则，因此直接使用 workflow version 定义中的全部 workflow input 名称作为 CSV 表头，不引入额外别名或嵌套映射。

这样可以：

- 与已有 run input contract 保持一一对应
- 让 batch 上传与单次 run 使用同一组输入定义
- 降低 CSV 解析和错误提示复杂度

### 3. Row 级校验失败不会阻塞整个 batch

CSV 中某一行输入非法时，该 item 会直接标记为失败，但 batch 仍继续处理其他合法行。这样可以避免一次批量提交被单行错误完全阻断。

### 4. Batch 内严格串行，一次只驱动一个 run

MVP 选择串行执行，原因是：

- 更容易复用现有单 run auto-drive 行为
- 避免并发 run 对本地 workspace / 调试资源造成混淆
- 让批次进度与结果页表达更直观

### 5. 批次详情页以 row-item 聚合为主，而不是复制 run 详情

批次页只负责回答三个问题：

- 这一批整体进度如何
- 每一行对应的 run 是什么状态
- 如何跳到单 run 详情或直接打开 workspace

深入调试仍回到既有 run 详情页处理，避免重复建设调试界面。

## Risks / Trade-offs

- [CSV 类型表达有限] -> 通过现有 workflow input 类型解析做基础转型，复杂结构继续使用 JSON 单元格文本。
- [长批次轮询成本增加] -> 仅在 `pending/running` 状态下高频轮询，终态后停止。
- [打开 workspace 是本地环境相关能力] -> 继续沿用当前本地 Studio 假设，只暴露明确的成功/失败反馈。

## Migration Plan

1. 增加 batch run 数据模型、仓储和服务层。
2. 增加模板下载、批次创建、批次详情和打开 workspace API。
3. 在 Workflow Studio 版本页增加批量启动入口。
4. 新增批次详情页并复用现有 run 详情和 workspace 打开能力。
5. 补充前后端测试后，将 delta spec 同步到主规格并归档 change。
