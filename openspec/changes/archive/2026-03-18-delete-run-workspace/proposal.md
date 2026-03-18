## Why

运行列表里的失败 run 会长期停留在“需关注”，即使操作者已经决定不再继续处理，也没有办法把这类 run 从列表和磁盘中清理掉。随着失败 run 累积，关注队列会失真，workspace 占用的磁盘空间也无法释放。

## What Changes

- 增加删除非运行中 run 的后端 API，并在删除时同时清理该 run 的 workspace 目录。
- 在运行列表和运行详情页增加删除入口，允许直接删除 `needs_attention`、`stopped`、`completed` run。
- 扩展 batch 详情返回与展示逻辑，保留批次历史行，但对已删除 run 明确标记“已删除”并禁用相关跳转/打开操作。

## Capabilities

### New Capabilities

### Modified Capabilities

- `run-operations`: 扩展运行管理能力，允许操作者永久删除非运行中 run，并在批量运行历史中保留已删除 run 的可见状态。

## Impact

- 后端 `RunService`、`WorkspaceManager`、运行与批次 API
- 前端 run 列表、run 详情、batch 详情与国际化文案
- 后端 API 测试与前端交互测试
