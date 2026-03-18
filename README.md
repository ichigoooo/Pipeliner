# Pipeliner

Pipeliner 是一个 Python-first 的 agent 工作流编排器 MVP。

当前版本已经跑通最小可交付闭环，并新增 Developer Workflow Studio：
- `workflow spec` 作为唯一机器真源
- `executor -> validator -> pass / revise / blocked` 最小状态机
- 统一 callback API
- 基于 `artifact manifest` 的交付物登记与不可变版本流转
- 本地 `run workspace` 目录追踪
- 最小 CLI / FastAPI / HTML inspection surface
- Developer Workflow Studio（Next.js）工作台、authoring session 与多视图 workflow workspace
- 真实 `Claude` executor / validator 接入
- `run drive` 自动顺序驱动 run 到终态
- 基于 CSV 的 batch run 模板下载、批量启动、串行调度与批次详情页
- Authoring 一键打开 workflow 项目目录，直观查看 skills 与脚本

## 当前进展

当前 MVP 后端核心已完成，已具备实际试跑能力；开发者工作台和 authoring 能力已就绪。

已完成：
- workflow 注册、版本加载与 run 启动
- node callback 协议、artifact manifest 协议与 runtime guards
- run / node run / callback / artifact 持久化
- executor 调度、validator 调度、超时协调、人工介入可见性
- 本地 workspace、产物落盘、manifest 发布、callback 归档
- 最小 CLI、API、HTML 只读检查界面
- Developer Workflow Studio 前端（authoring / workflows / runs / attention / settings）
- authoring session、draft revision、lint gating、publish
- workflow 多视图同步（cards / graph / spec / lint）
- run 调试聚合视图与手动介入（retry / stop）
- settings 溯源面板（生效值 + 来源）
- batch run 数据模型、CSV 模板生成、逐行校验与串行调度
- Workflow Studio 批量启动入口、批次详情页与一键打开 run workspace
- Authoring 操作区一键打开 workflow 项目目录
- runs/batches 批量删除与历史保留标记，降低运行列表噪音
- Claude 连接诊断（base URL / API host / proxy 摘要）与 settings 展示
- Claude 慢启动告警与预检失败提示，避免“无输出=空闲”的误判

已验证：
- 后端自动化测试通过：`83 passed`
- 前端 Vitest 通过：`25 passed`
- 真实 `Claude` 联调通过
- 一条真实 run 已从启动推进到 `completed`

## 当前能力

当前可以完成以下操作：
- 注册 `workflow spec`
- 启动 `run`
- 查看 run、node、artifact、callback 状态
- 在 Studio 里调用 Claude 生成草案并形成新 revision
- 用真实 `Claude` 执行 executor 节点
- 用真实 `Claude` 执行 validator 节点
- 用 `run drive` 自动顺序驱动整个 run
- 在 `blocked`、`failed`、`timed_out`、`rework_limit` 时停在人工介入边界
- 从已发布版本或 attention run 发起迭代会话
- 预览 artifact payload 与 run log 片段
- 使用 Workflow Studio 完成 authoring、workflow 浏览、run 调试与 settings 溯源
- 通过 CSV 模板批量启动多条 run，并在批次详情页追踪每一行状态
- 在 Authoring 中一键打开 workflow 项目目录并检查 skills / scripts
- 在 `/runs` 和 batch 列表中批量清理已结束条目并保留批次历史
- 在无 Claude 输出时区分排队、慢启动、预检失败和真实超时
- 在 `/settings` 查看 Claude 连接诊断来源，快速定位网络与代理问题

## 技术栈

- `Python 3.12+`
- `FastAPI`
- `Pydantic v2`
- `SQLAlchemy 2.x`
- `Alembic`
- `Typer`
- `SQLite`
- `pytest`
- `Next.js`
- `React + TypeScript`
- `TanStack Query`
- `React Flow`
- `CodeMirror`
- `Tailwind CSS`
- `Vitest`

## 构建与启动

### 一键启动（推荐）

先准备环境变量文件：

```bash
cp ".env.example" ".env"
cp "web/.env.local.example" "web/.env.local"
chmod +x "scripts/dev-up.sh"
```

然后直接启动前后端：

```bash
"./scripts/dev-up.sh"
```

脚本会自动执行以下动作：
- 加载根目录 `.env` 与 `web/.env.local`
- 执行 `uv sync`
- 执行数据库迁移与 `db-init`
- 启动后端 `FastAPI`
- 启动前端 `Next.js`

默认地址：
- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:3000`

### 后端（API + Runtime）

```bash
uv sync
uv run alembic upgrade head
uv run pipeliner db-init
uv run uvicorn pipeliner.app:create_app --factory --reload
```

默认监听 `http://127.0.0.1:8000`，API 文档在 `/docs`。

### 前端（Workflow Studio）

```bash
cd web
npm install
npm run dev
```

默认启动 `http://localhost:3000`，前端会通过 `/api/*` 代理到后端。

### 构建（生产）

```bash
cd web
npm run build
npm run start
```

## 使用说明

### Workflow Studio（推荐入口）

详细步骤见 `docs/studio-usage.md`。

1. 打开 `http://localhost:3000`
2. 进入 `/authoring` 创建 authoring session（或从版本/attention 发起迭代）
3. 在右侧编辑 canonical spec，保存、继续或使用 Claude 生成新草案
4. 在 Authoring 操作区点击 `Open Project Folder` 打开 `projects/<workflow_id>/` 查看 metadata、skills 与脚本
5. lint 通过后发布为 workflow version
6. 在 `/workflows` 选择版本并点击 `Start Run`
7. 在 `/runs` 或 `/runs/{run_id}` 查看 timeline、callbacks、artifacts、context 与 log refs
8. 在 run 详情中执行自动驱动，查看 stop reason 与步骤摘要
9. 点击 artifact / log 预览内容（超限会提示路径）
10. 在 `/attention` 处理中断状态并执行 retry/stop/迭代
11. 在 `/settings` 查看运行时配置与来源

每个 workflow 会在 `projects/<workflow_id>/` 下生成工程目录，并自动创建 `.claude/skills/`。Authoring 生成时会优先使用这些 skills（workflow-authoring / workflow-iteration / workflow-review）。

### Batch Run（CSV 批量启动）

适用于同一 `workflow version` 需要用多组输入顺序执行的场景。

1. 打开 `/workflows/{workflow_id}/{version}`
2. 点击 `Download Template` 下载模板 CSV
3. 按表头填写每一行 workflow inputs
4. 点击 `Batch Launch`，上传 CSV 并创建批次
5. 页面会跳转到 `/runs/batches/{batch_id}`
6. 在批次详情页查看总数、成功数、失败数、逐行状态和对应 `run_id`
7. 对已有 `run_id` 的行可直接进入 run 详情，或点击 `Open Folder` 打开本地 run workspace

说明：
- CSV 表头直接等于该 workflow version 的全部 workflow input 名称
- 每一行会生成一个 batch item
- 合法行按顺序串行执行，一次只会驱动一个 run
- 非法行会标记为失败，但不会阻塞其他合法行继续执行
- 批次详情页在 `pending` / `running` 状态下会自动刷新

### 最小 CLI 使用流

1. 注册 workflow spec
2. 启动 run，并写入 workflow inputs
3. 使用 `run drive` 自动驱动，或手动逐节点执行 `executor dispatch` / `validator dispatch`
4. 通过 CLI / API / HTML 页面检查运行状态

如果不走自动驱动，也支持手动模式：

1. 在 run workspace 下准备 artifact payload 文件
2. 发布 artifact manifest
3. 让 executor / validator 通过 callback API 回报结果

## CLI

```bash
uv run pipeliner workflow register tests/fixtures/workflows/mvp_review_loop.json
uv run pipeliner run start mvp-review-loop 0.1.0 tests/fixtures/run_inputs.json
uv run pipeliner run show <run_id>
uv run pipeliner run attention
uv run pipeliner run drive <run_id>
uv run pipeliner run reconcile-timeouts
uv run pipeliner executor dispatch <run_id> <node_id>
uv run pipeliner validator dispatch <run_id> <node_id> <validator_id>
```

`executor dispatch` 会读取节点 `executor/context.json`，调用配置的 Claude 命令生成产物，自动发布 artifact manifest，并自动提交 executor callback。
`validator dispatch` 会读取 validator context，调用配置的 Claude 命令生成结构化判定结果，并自动提交 validator callback。
`run drive` 会顺序调度当前 run 中所有可执行的 executor / validator，直到 run 进入 `completed`、`needs_attention`、`stopped` 或达到 `max_steps`。

可通过环境变量覆盖命令模板：

```bash
export PIPELINER_CLAUDE_EXECUTOR_CMD='claude -p --permission-mode bypassPermissions'
export PIPELINER_CLAUDE_VALIDATOR_CMD='claude -p --permission-mode bypassPermissions'
export PIPELINER_CLAUDE_AUTHORING_CMD='claude -p --permission-mode bypassPermissions'
export PIPELINER_AUTHORING_TIMEOUT='20m'
```

如需对 Claude 输出做强校验，可使用包装脚本：

```bash
export PIPELINER_CLAUDE_AUTHORING_CMD='python scripts/authoring/claude_authoring_wrapper.py --prompt-file {prompt_file} --task-file {task_file} --result-file {result_file} --work-dir {work_dir}'
export PIPELINER_CLAUDE_AUTHORING_INNER_CMD='claude -p --permission-mode bypassPermissions'
```

支持模板占位符：`{prompt_file}`、`{task_file}`、`{work_dir}`。
调度器会把节点 prompt 通过 stdin 传入命令（默认模板为 `claude -p --permission-mode bypassPermissions`）。
如果模板不含占位符且只有一个命令词，系统会把 `prompt_file` 作为末尾参数附加。

## API / UI

- API 文档：`/docs`
- 首页：`/`
- Workflow 只读视图：`/ui/workflows/{workflow_id}/versions/{version}`
- Run 只读视图：`/ui/runs/{run_id}`
- Workflow Studio：`http://localhost:3000`
- Studio 入口：`/authoring`、`/workflows`、`/runs`、`/runs/batches/{batch_id}`、`/attention`、`/settings`
- Executor 调度接口：`POST /api/runs/{run_id}/nodes/{node_id}/executor/dispatch`
- Validator 调度接口：`POST /api/runs/{run_id}/nodes/{node_id}/validators/{validator_id}/dispatch`
- Batch 模板下载接口：`GET /api/workflows/{workflow_id}/versions/{version}/inputs/template.csv`
- Batch 创建接口：`POST /api/workflows/{workflow_id}/versions/{version}/batch-runs`
- Batch 详情接口：`GET /api/batch-runs/{batch_id}`
- 打开 run workspace 接口：`POST /api/runs/{run_id}/open-folder`

## Canonical Workflow View

MVP 中，`workflow spec` 是唯一机器真源。
任何面向人类的视图，包括 HTML 页面，都是从注册后的 spec 派生出的只读视图，而不是独立 authoring 真源。

Workflow Studio 中的 cards / graph / spec / lint 与 raw inspector 都来自同一 canonical draft 或已发布版本。

## Run Workspace 约定

每个 run 在本地都有独立工作目录：

```text
.pipeliner/
└─ runs/
   └─ <workflow_id>/
      └─ <run_id>/
         ├─ inputs/workflow_inputs.json
         ├─ nodes/<node_id>/rounds/<round_no>/...
         ├─ artifacts/<artifact_id>@<version>/manifest.json
         └─ callbacks/<event_id>.json
```

其中：
- `inputs/` 保存 workflow 输入快照
- `nodes/` 保存 executor/validator handoff context
- `artifacts/` 保存 manifest 元数据，payload 由 manifest 的 `storage.uri` 指向
- `callbacks/` 保存 callback 原始归档

## 后续计划

下一阶段优先做以下几项：
- 增加更完整的人工恢复与重试操作，例如继续执行、重跑当前节点、处理 `needs_attention`
- 增强 batch run 能力，例如并发策略、批次级重试、暂停/恢复与更细粒度的输出限制
- 增加更清晰的 operator 界面，降低查看 run / node / artifact / batch 状态的成本
- 在核心稳定后，再逐步补强产品化 UI/UX，而不是提前做复杂前端

## 环境变量

后端常用：

```bash
export PIPELINER_DATA_DIR=".pipeliner"
export PIPELINER_CLAUDE_EXECUTOR_CMD="claude -p --permission-mode bypassPermissions"
export PIPELINER_CLAUDE_VALIDATOR_CMD="claude -p --permission-mode bypassPermissions"
```

前端代理后端地址（可选）：

```bash
export PIPELINER_API_BASE_URL="http://127.0.0.1:8000"
export PIPELINER_API_HEADERS_TIMEOUT_MS=1800000
export PIPELINER_API_BODY_TIMEOUT_MS=1800000
```

建议直接复制模板后按需修改：

```bash
cp ".env.example" ".env"
cp "web/.env.local.example" "web/.env.local"
```

如果需要自定义数据库，再额外设置：

```bash
export PIPELINER_DATABASE_URL="sqlite:////absolute/path/to/pipeliner.db"
```
