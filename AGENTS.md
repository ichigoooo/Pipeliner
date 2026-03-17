# Repository Guidelines

本文件为 Agent 编程助手提供项目结构、命令和代码规范指引。

## 项目概述

Pipeliner 是一个 Python-first 的 agent 工作流编排器，采用 workflow spec 作为唯一机器真源，通过 executor -> validator -> pass/revise/blocked 状态机驱动工作流执行。

- **Python 版本**: 3.12+
- **主要框架**: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Next.js
- **测试框架**: pytest (后端), Vitest (前端)

---

## 项目结构

```
src/pipeliner/
├── protocols/           # 领域协议定义 (Pydantic 模型)
│   ├── workflow.py      # WorkflowSpec、NodeSpec
│   ├── callback.py      # NodeCallbackPayload、VerdictStatus
│   ├── artifact.py      # ArtifactManifest、ArtifactRef
│   └── guards.py        # RuntimeGuards
├── services/            # 业务逻辑服务
│   ├── run_service.py   # Run 生命周期管理
│   ├── run_driver.py    # 自动驱动调度
│   ├── workflow_service.py
│   └── errors.py        # 统一异常定义
├── persistence/         # SQLAlchemy 模型与 Repository
├── executor/            # Claude 调度器实现
├── api/router.py        # FastAPI 路由
├── storage/             # 本地文件系统 WorkspaceManager
├── config.py            # Settings (环境变量驱动)
└── cli.py               # Typer CLI

tests/
├── conftest.py          # pytest fixtures
├── test_*.py           # 单元测试
├── api/test_*.py       # API 集成测试
└── fixtures/           # 测试数据

web/                     # Next.js 前端
├── src/app/             # App Router 页面
├── src/components/      # React 组件
├── vitest.config.ts     # 前端测试配置
└── package.json
```

---

## 开发命令

### 后端 (Python)

```bash
# 安装依赖
uv sync

# 数据库迁移
uv run alembic upgrade head
uv run pipeliner db-init

# 启动开发服务器
uv run uvicorn pipeliner.app:create_app --factory --reload

# 代码检查 (推荐先运行)
uv run ruff check .

# 测试
uv run pytest                          # 运行全部测试
uv run pytest tests/test_runtime.py   # 运行单个测试文件
uv run pytest -k test_name           # 按名称过滤运行
uv run pytest tests/test_runtime.py::test_timeout_reconcile_marks_waiting_node_as_attention -v  # 运行单个测试

# 更详细的测试输出
uv run pytest -v -s --tb=short
```

### 前端 (Next.js)

```bash
cd web

# 安装依赖
npm install

# 开发
npm run dev                # localhost:3000

# 测试
npm run test              # Vitest
npm run test -- --run     # 单次运行 (非 watch 模式)

# 构建
npm run build
npm run start
```

### 一键启动 (推荐)

```bash
./scripts/dev-up.sh
```

---

## 代码规范

### 通用规范

- **缩进**: 4 空格 (Python), 2 空格 (前端)
- **行长**: 最大 100 字符
- **类型标注**: 必须使用类型标注 (Python)
- **导入顺序**: 标准库 → 第三方库 → 本地模块 (Python)

### Python 规范

```python
# 必须使用 from __future__ import annotations
from __future__ import annotations

# 类型标注使用 | 而非 Union
def foo(x: str | None) -> int | None: ...

# Pydantic 模型
class WorkflowSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    workflow_id: str
    version: str
    nodes: list[WorkflowNodeSpec]

# 异常定义 (统一在 services/errors.py)
class NotFoundError(PipelinerError):
    pass

# 错误消息使用中文
raise NotFoundError(f"未找到 run: {run_id}")
```

### 前端规范

- 使用 TypeScript 类型标注
- 组件使用 functional component + hooks
- 样式使用 Tailwind CSS
- 国际化使用 `next-intl`，翻译键遵循 `page.component.element` 层级

### 文件命名

- Python 模块: `snake_case.py` (如 `run_service.py`)
- React 组件: `PascalCase.tsx` (如 `RunDetail.tsx`)
- 测试文件: `test_*.py` 或 `*_test.py`

### 目录命名

- 业务模块: `snake_case` (如 `services/`, `persistence/`)
- 协议定义: `protocols/`
- 测试目录: 与源码对应，如 `tests/api/`, `tests/persistence/`

---

## 测试规范

### pytest fixtures (tests/conftest.py)

```python
@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / ".pipeliner", ...)

@pytest.fixture()
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
```

### 测试文件组织

- `tests/test_*.py`: 单元测试
- `tests/api/test_*.py`: API 集成测试 (使用 TestClient)
- `tests/persistence/test_*.py`: 数据库 Repository 测试

### 测试数据

- 使用 `tests/fixtures/` 存放 JSON/YAML 测试数据
- Workflow fixture: `tests/fixtures/workflows/mvp_review_loop.json`

---

## 错误处理

### 统一异常类 (services/errors.py)

```python
class PipelinerError(Exception):
    pass

class NotFoundError(PipelinerError):
    pass

class ConflictError(PipelinerError):
    pass

class InvalidStateError(PipelinerError):
    pass

class ValidationError(PipelinerError):
    pass
```

### API 错误响应

- 使用 FastAPI 的 `@app.exception_handler` 统一处理
- 返回结构化错误 JSON

---

## 数据库迁移

```bash
# 创建迁移
uv run alembic revision --autogenerate -m "add_xxx"

# 升级
uv run alembic upgrade head

# 回滚
uv run alembic downgrade -1
```

---

## OpenSpec 变更工作流

本仓库使用 OpenSpec 变更流程：

1. **探索模式**: 使用 `/opsx explore` 讨论需求
2. **新建变更**: 使用 `/opsx new` 创建 proposal → design → tasks
3. **实现**: 使用 `/opsx apply` 执行 tasks
4. **验证**: 使用 `/opsx verify` 确认实现完整
5. **归档**: 使用 `/opsx archive` 归档变更

变更文件位于 `openspec/changes/`，包含:
- `proposal.md`: 变更提案
- `design.md`: 设计方案
- `tasks.md`: 任务清单
- `specs/`: 各子域详细规格

---

## 安全与配置

### 不要提交

- 本地数据库文件 (`.pipeliner/`)
- API 密钥、环境变量文件 (`.env`)
- 大体积 artifact 文件
- 临时运行产物

### 环境变量

```bash
# 后端
PIPELINER_DATA_DIR=".pipeliner"
PIPELINER_CLAUDE_EXECUTOR_CMD="claude -p --permission-mode bypassPermissions"
PIPELINER_CLAUDE_VALIDATOR_CMD="claude -p --permission-mode bypassPermissions"

# 前端代理
PIPELINER_API_BASE_URL="http://127.0.0.1:8000"
```

---

## 提交规范

### 提交信息格式

使用简短祈使句，聚焦单一变更：

```
add workflow runtime spec
fix run status refresh bug
implement batch run CSV template
```

### PR 描述

- 变更目的
- 影响目录
- 关联的 `openspec/changes/...` 路径
- 如有 UI 变更，提供截图或 GIF
