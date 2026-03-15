## Why

当前 Workflow Studio 只能一次启动一个 run。对于需要批量处理多组输入的场景，操作员必须重复填写表单或手动构造请求，效率低且容易出错，也无法集中查看这一批输入对应的执行结果。

## What Changes

- 为工作流版本提供基于全部 workflow inputs 生成的 CSV 模板下载能力。
- 支持上传 CSV 创建 batch run，并将每一行输入映射为一个待执行项。
- 在 batch 内按顺序串行执行，每次只启动并驱动一个 run。
- 提供批次详情视图，聚合展示每一行的 run 状态、错误信息、结果入口，并支持直接打开 run workspace。

## Capabilities

### Modified Capabilities

- `run-operations`: 启动运行的能力从单次 run 扩展到批量 run，包含模板下载、CSV 上传、串行调度和批次详情查看。

## Impact

- 影响后端运行编排与持久化模型，需新增 batch run 及其 item 跟踪。
- 影响工作流版本页和运行页导航，需增加批量启动入口与批次详情页面。
- 影响 Studio API 代理与前端 API 客户端，需支持 `multipart/form-data` 上传和批次查询接口。
