# Pipeliner Release Readiness

日期：2026-05-18 15:41 CST

## 结论

当前产品代码、规格和测试已收口到可提交、可 release 的状态。

本次收口完成：

- 后端 lint 基线恢复为全仓 `uv run ruff check .` 通过。
- 后端测试通过。
- 前端测试、lint、生产构建通过。
- Next.js 生产构建从默认 Turbopack 切换为稳定的 webpack 构建路径。
- `productize-studio-polish` OpenSpec change 已同步主规格并归档。
- `git diff --check` 通过。

## 主要变更

### Runtime / Claude 调用

- executor / validator 失败路径区分 `failed` 与 `timeout`。
- validator 非完成态 callback 可不携带 verdict。
- runtime 对 retryable failure 支持自动重试延迟。
- run driver 在可重试失败后等待短延迟再继续调度。
- Claude 调用元数据包含慢启动和预检失败信息。
- settings / authoring / executor / validator 共享 Claude 环境诊断口径。

### Studio

- `/runs` 按 actionable / active / archived 分组。
- runs 和 batches 支持批量清理非活动项。
- batch row 在 run 删除后保留 deleted 历史状态。
- run detail 支持当前焦点跟随和历史轮次固定查看。
- 终端无输出时展示排队、已启动无输出、慢启动、预检失败等状态解释。
- settings 展示 Claude base URL、API host、proxy 摘要及来源。
- 引入 `StudioPage` 统一 Studio 页面布局。

### Release 基线

- `pyproject.toml` 排除 `alembic/versions` 和 `projects` 的 ruff 检查。
  - 迁移历史和 workflow 运行工作区不作为产品源码 lint 范围。
  - `alembic/env.py` 仍保留在 ruff 范围内。
- `web/package.json` 的 build 脚本改为 `next build --webpack`。
- `web/next.config.ts` 设置 `outputFileTracingRoot`，避免 workspace root 误判警告。
- `scripts/authoring/claude_authoring_wrapper.py` 修复 B904。
- OpenSpec 主规格已同步：
  - `developer-console`
  - `run-operations`
  - `authoring-agent`
  - `claude-terminal-live-ui`
- OpenSpec 归档路径：
  - `openspec/changes/archive/2026-05-18-productize-studio-polish/`

## 验收命令

### 后端 lint

```bash
uv run ruff check .
```

结果：

```text
All checks passed!
```

### 后端测试

```bash
uv run pytest
```

结果：

```text
89 passed in 13.78s
```

### 前端测试

```bash
cd web
npm run test
```

结果：

```text
Test Files  13 passed (13)
Tests       28 passed (28)
```

### 前端 lint

```bash
cd web
npm run lint
```

结果：通过，无错误输出。

### 前端生产构建

```bash
cd web
npm run build
```

结果：

```text
Compiled successfully
Generated static pages: 9/9
```

### OpenSpec

```bash
openspec list --json
```

结果：

```json
{"changes":[]}
```

备注：OpenSpec CLI 结束后仍会尝试发送 PostHog telemetry，并因当前网络无法解析 `edge.openspec.dev` 输出错误。这不影响本地 change 校验和归档结果。

### Diff 检查

```bash
git diff --check
```

结果：通过，无输出。

## 提交边界建议

建议本次 release commit 包含：

- `src/`
- `tests/`
- `web/`
- `openspec/specs/`
- `openspec/changes/archive/2026-05-18-productize-studio-polish/`
- `pyproject.toml`
- `alembic/env.py`
- `scripts/authoring/claude_authoring_wrapper.py`
- `temp/project-progress-acceptance-20260518.md`
- `temp/release-readiness-20260518.md`

需要单独决策的本地现场：

- `projects/classical-text-to-csv/` 下仍有大量修改和未跟踪文件。
- 这些看起来是真实 workflow 项目试跑产物或辅助脚本，不建议在未确认用途前混入 release commit。
- 当前 ruff 已明确排除 `projects/`，避免运行产物影响产品代码质量基线。

## 建议提交信息

```text
stabilize workflow studio release baseline
```
