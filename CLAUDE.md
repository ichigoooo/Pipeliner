# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Pipeliner 是一个 Python-first 的 agent 工作流编排器，采用 workflow spec 作为唯一机器真源，通过 executor -> validator -> pass/revise/blocked 状态机驱动工作流执行。

## 常用命令

### 开发启动（推荐）
```bash
./scripts/dev-up.sh        # 一键启动前后端（自动处理端口冲突、数据库迁移、依赖安装）
```

### 后端开发
```bash
uv sync                    # 同步 Python 依赖
uv run alembic upgrade head # 执行数据库迁移
uv run pipeliner db-init   # 初始化数据库
uv run uvicorn pipeliner.app:create_app --factory --reload  # 启动开发服务器

# 测试
uv run pytest              # 运行全部测试
uv run pytest tests/test_runtime.py -v  # 运行单个测试文件
uv run pytest -k test_name # 运行指定测试
```

### 前端开发
```bash
cd web
npm install
npm run dev                # 启动 Next.js 开发服务器 (localhost:3000)
npm run build              # 构建生产版本
npm run test               # 运行 Vitest 测试
```

### CLI 常用命令
```bash
uv run pipeliner workflow register tests/fixtures/workflows/mvp_review_loop.json
uv run pipeliner run start mvp-review-loop 0.1.0 tests/fixtures/run_inputs.json
uv run pipeliner run show <run_id>
uv run pipeliner run drive <run_id>          # 自动驱动 run 到终态
uv run pipeliner run attention               # 查看需要人工介入的 run
uv run pipeliner run reconcile-timeouts      # 超时检查
uv run pipeliner executor dispatch <run_id> <node_id>
uv run pipeliner validator dispatch <run_id> <node_id> <validator_id>
```

## 架构概览

### 核心组件

```
src/pipeliner/
├── protocols/             # 领域协议定义
│   ├── workflow.py        # WorkflowSpec、NodeSpec、输入输出规范（Pydantic 模型）
│   ├── callback.py        # NodeCallbackPayload、ExecutionStatus、VerdictStatus
│   ├── artifact.py        # ArtifactManifest、ArtifactRef
│   └── guards.py          # RuntimeGuards（超时、最大重做次数）
├── runtime/
│   └── coordinator.py     # RuntimeCoordinator：回调提交、超时协调、状态机推进
├── services/
│   ├── run_service.py     # RunService：run 生命周期、node 激活、context 构建
│   ├── run_driver.py      # RunDriver：自动顺序驱动 executor/validator 调度
│   ├── workflow_service.py # WorkflowService：workflow 注册、lint、版本管理
│   ├── authoring_service.py # AuthoringSession、Draft、Publish 流程
│   ├── artifact_service.py # Artifact 解析、manifest 发布
│   └── settings_service.py # 配置溯源（生效值+来源）
├── persistence/           # SQLAlchemy 模型与 Repository 模式
├── executor/              # Claude 调度器实现
├── api/router.py          # FastAPI 路由（约 600 行核心 API 实现）
├── storage/               # 本地文件系统 WorkspaceManager
└── config.py              # Settings（环境变量驱动，单例模式）
```

### Node 生命周期状态机

```
PENDING -> WAITING_EXECUTOR -> WAITING_VALIDATOR -> PASSED
                |                      |
                v                      v
             FAILED                 BLOCKED
             TIMED_OUT              REVISE (循环)
             (NEEDS_ATTENTION)      REWORK_LIMIT
```

### Run Workspace 目录结构

每个 run 在 `.pipeliner/runs/<workflow_id>/<run_id>/` 下有独立工作目录：

```
inputs/workflow_inputs.json              # 输入快照
nodes/<node_id>/rounds/<round_no>/
  ├── executor/context.json              # executor handoff context
  ├── executor/prompt.txt                # 生成的 prompt
  └── validators/<validator_id>/context.json  # validator context
artifacts/<artifact_id>@<version>/manifest.json  # 产物 manifest
callbacks/<event_id>.json                # callback 归档
```

### 关键设计约定

1. **Workflow Spec 是唯一真源**：`schema_version: pipeliner.workflow/v1alpha1`，JSON 格式定义在 `protocols/workflow.py`
2. **Callback API 统一协议**：executor/validator 通过 `POST /callbacks` 提交结果，RuntimeCoordinator 处理状态转换
3. **Artifact Manifest**：产物元数据与 payload 分离，manifest 存数据库/JSON，payload 由 `storage.uri` 指向
4. **运行时保护**：timeout、max_rework_rounds、blocked_requires_manual 等 guards 配置
5. **真实 Claude 集成**：通过 `PIPELINER_CLAUDE_EXECUTOR_CMD` 环境变量配置调用模板，支持占位符 `{prompt_file}`、`{task_file}`、`{work_dir}`

### 前端架构

```
web/src/
├── app/(studio)/          # Studio 路由组
│   ├── authoring/         # 创作会话（draft editing、lint、publish）
│   ├── workflows/         # workflow 浏览、版本查看、启动 run
│   ├── runs/[run_id]/     # run 调试视图（timeline、callbacks、artifacts）
│   ├── attention/         # 中断处理（retry/stop）
│   └── settings/          # 配置溯源面板
├── components/
│   ├── workflow/          # WorkflowWorkspace（cards/graph/spec/lint 多视图）
│   └── authoring/         # AuthoringWorkspace
└── app/api/               # Next.js API routes（代理到后端）
```

### i18n 国际化

- 使用 `next-intl` 进行国际化，支持英语 (`en`) 和中文 (`zh`)
- 翻译文件位于 `web/src/i18n/messages/`，按语言分文件存储
- 翻译键命名规范：`page.component.element` 层级结构
  - 例如：`settings.language.title`、`sidebar.nav.workflows`、`common.save`
- 使用 `useTranslations` hook 获取翻译函数：`const t = useTranslations('namespace')`
- 语言状态使用 Zustand 管理，持久化到 localStorage
- **开发流程要求**：新 UI 必须同时添加中英文翻译

### 数据库模型关系

- WorkflowDefinition → WorkflowVersion（一对多）
- Run（关联 WorkflowVersion）→ NodeRun（一对多）
- NodeRun → CallbackEvent（一对多）
- Artifact（独立表，通过 artifact_id@version 寻址）
- AuthoringSession → DraftVersion（一对多）

## 测试策略

- 后端：pytest + FastAPI TestClient，`conftest.py` 提供 fixtures（settings、client、workflow_fixture）
- 前端：Vitest + React Testing Library + jsdom
- 测试数据：`tests/fixtures/workflows/` 包含 mvp_review_loop.json 等示例 workflow
