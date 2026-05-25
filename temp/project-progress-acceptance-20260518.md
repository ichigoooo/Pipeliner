# Pipeliner 项目进度验收记录

日期：2026-05-18

## 背景

本次验收目标是回顾 Pipeliner 长时间搁置后的当前开发进度，确认项目能否作为下一轮迭代优化的基线。

结论：项目已经超过早期 MVP 阶段，当前处于 Workflow Studio 产品化收口阶段。主闭环已具备实际使用能力，但仓库现场仍有未提交改动、后端 lint 基线不干净，以及前端生产构建疑似卡住的问题需要优先收口。

## 当前能力基线

已具备的主要能力：

- Authoring 会话、Claude 生成、草案保存、发布 workflow version。
- Workflow 注册、版本浏览、输入表单与 run 启动。
- Run 自动 drive、手动 dispatch、attention 介入、retry / stop。
- Executor / validator 接入真实 Claude 命令。
- Artifact、callback、log、run workspace 的持久化和预览。
- Batch run CSV 模板、批量启动、串行调度和批次详情页。
- Workflow Studio 页面：`/authoring`、`/workflows`、`/runs`、`/attention`、`/settings`。
- Claude 连接诊断：base URL、API host、proxy 摘要、慢启动与预检失败提示。
- Runs / batches 批量删除与历史保留标记。
- Run detail 当前焦点跟随与历史轮次固定查看。

## OpenSpec 状态

当前活跃变更：

- `productize-studio-polish`
- 任务进度：`13/13`
- 状态：complete
- 校验命令：`openspec validate productize-studio-polish --strict`
- 校验结果：通过

注意：该 change 已完成但尚未归档。下一轮正式迭代前建议先归档或同步主规格，避免实现、文档和 OpenSpec 状态继续漂移。

## 验收命令结果

### 后端测试

命令：

```bash
uv run pytest
```

结果：

```text
89 passed in 12.66s
```

### 前端测试

命令：

```bash
npm run test
```

结果：

```text
Test Files  13 passed (13)
Tests       28 passed (28)
```

### 前端 lint

命令：

```bash
npm run lint
```

结果：通过，无错误输出。

### OpenSpec 校验

命令：

```bash
openspec validate productize-studio-polish --strict
```

结果：`Change 'productize-studio-polish' is valid`

备注：命令结束后 OpenSpec telemetry 尝试访问 `edge.openspec.dev` 失败，这是网络/遥测问题，不影响 change 校验结果。

### 后端 lint

命令：

```bash
uv run ruff check .
```

结果：失败，约 `588` 个问题。

主要来源：

- Alembic 历史迁移文件格式问题。
- `projects/` 下生成的 workflow skill 脚本格式问题。
- 核心 `src` / `tests` 中的导入排序、行长、少量未使用导入。

进一步聚焦命令：

```bash
uv run ruff check src tests
```

结果：失败，`83` 个问题。

主要类型：

- `I001` 导入排序。
- `E501` 行长超过 100。
- `F401` 未使用导入。
- `B008` FastAPI `File(...)` 作为默认参数。
- `B904` except 内 raise 链接不明确。

### 前端生产构建

命令：

```bash
npm run build
```

结果：未完成。

观察：

- 构建停留在 `Creating an optimized production build ...`。
- 等待约 2 分钟无进一步输出。
- 已终止本次检查启动的构建进程，避免后台悬挂。

结论：前端测试和 lint 健康，但生产构建需要单独排查。

## Git 工作现场

当前分支：

```text
main...origin/main
```

存在大量未提交改动。

核心代码改动集中在：

- `src/pipeliner/executor/claude_executor.py`
- `src/pipeliner/executor/claude_validator.py`
- `src/pipeliner/protocols/callback.py`
- `src/pipeliner/runtime/coordinator.py`
- `src/pipeliner/services/run_driver.py`
- `src/pipeliner/services/run_service.py`
- 多个 API / runtime / executor 相关测试。
- Studio 多个页面和共享 UI 组件。

主要主题：

- executor / validator 失败和 timeout 语义收口。
- retryable failure 和自动重试延迟。
- validator failed callback 允许无 verdict。
- run detail 当前焦点和历史轮次体验。
- runs / batches 分组、批量清理和删除历史标记。
- settings Claude 诊断展示。
- Studio 页面视觉统一与 `StudioPage` 组件引入。

另有 `projects/classical-text-to-csv/` 下大量修改和新增文件，像是真实 workflow 项目试跑产生的运行现场或生成物。下一步需要判断这些文件是否应纳入版本控制。

## 风险与待处理

优先级较高：

1. 确认并收口未提交改动，区分产品代码、测试、文档和 workflow 运行产物。
2. 修复 `ruff check src tests`，建立核心代码 lint 基线。
3. 排查 `npm run build` 卡住问题。
4. 归档或同步 `productize-studio-polish`。

中等优先级：

1. 决定 Alembic 历史迁移和 `projects/` 生成物是否纳入全仓 ruff 范围。
2. 整理 `projects/classical-text-to-csv/` 下未跟踪脚本和 `.claude/skills` 变更。
3. 根据真实使用反馈继续压实 Claude 调用失败分类、慢启动提示和 settings 诊断。

## 建议下一步

建议先做一次“基线收口”变更，而不是立刻扩展新功能：

1. 保留并整理这轮 `productize-studio-polish` 相关产品改动。
2. 清理或隔离 `projects/` 下真实运行产物。
3. 修复核心 lint。
4. 重新运行后端测试、前端测试、前端 lint 和生产构建。
5. 归档 OpenSpec change。

完成后，项目就适合作为下一轮体验优化或稳定性增强的干净起点。
