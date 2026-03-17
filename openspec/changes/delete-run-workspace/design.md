## Overview

本次变更只在 `run` 级别提供永久删除能力，不引入 workflow/version 级删除，也不做软删除。目标是让操作者在决定放弃某次失败或历史运行后，能够同时清理运行列表中的记录与磁盘上的 workspace。

## Decisions

### 删除范围

- 允许删除 `needs_attention`、`stopped`、`completed` run。
- 禁止删除 `running` run，沿用现有 `InvalidStateError` 作为状态校验失败返回。

### 删除语义

- 采用永久删除，不增加数据库字段、不做回收站。
- 删除成功的定义是：数据库中的 run 及其级联数据被删除，且 `data_dir/runs/<workflow_id>/<run_id>` 目录被删除。
- 如果 workspace 目录已经不存在，仍视为可删除，不阻塞数据库删除。

### 事务与失败处理

- `RunService.delete_run()` 先读取 run 并校验状态，记录 `batch_id` 与 `workspace_root`。
- 在同一 SQLAlchemy session 中执行 `session.delete(run)` 并 `flush()`，先验证数据库级联删除没有问题。
- 文件系统删除失败时抛错，由 router 回滚整个请求，避免出现“数据库删了但目录还在”或“目录删了但数据库没删”的不一致。
- 文件系统删除完成后再 `commit()`。

### Batch 历史保留

- 不修改 `batch_run_items` 表结构，也不清空 `run_id`。
- batch 详情通过 `run_id` 是否仍存在于 `runs` 表中计算 `run_deleted`，用于前端展示。
- 这样可以保留原始批次历史，同时避免引入迁移。

## API Changes

- 新增 `DELETE /api/runs/{run_id}`
  - 成功返回：`run_id`、`workflow_id`、`batch_id`、`workspace_root`、`deleted: true`
  - `running` run 返回 400
  - run 不存在返回 404
- 扩展 `GET /api/batch-runs/{batch_id}`
  - `items[]` 新增 `run_deleted: boolean`

## Frontend Changes

- 运行列表页：每张非运行中卡片增加删除按钮，使用原生 `window.confirm` 二次确认。
- 运行详情页：在操作区增加删除按钮；删除成功后返回 `/runs`。
- batch 详情页：`run_deleted=true` 时保留 `run_id` 文本，显示“run 已删除”，隐藏 run 链接和打开目录按钮。

## Testing

- API：覆盖 attention/completed/stopped 删除成功、running 删除失败、batch run 删除后历史保留、workspace 缺失时仍可删除。
- Frontend：覆盖 runs 列表按钮展示与删除、run 详情删除跳转、batch 详情已删除标记展示。
