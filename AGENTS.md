# Repository Guidelines

## Project Structure & Module Organization
本仓库当前是 **spec-first** 项目，核心内容集中在设计与变更说明，而不是运行时代码。

- `docs/`：架构、协议与技术选型文档，例如 `docs/tech-stack-decision.md`。
- `openspec/changes/implement-pipeliner-mvp/`：当前 MVP 变更提案，包含 `proposal.md`、`design.md`、`tasks.md` 以及各子域 `spec.md`。
- `temp/`：临时评审材料，仅作讨论输入，不应作为长期真源。
- `.codex/`：本地自动化与技能配置，不承载产品逻辑。

当前尚未提交 `src/` 或 `tests/`。后续落地 Python 实现时，建议将应用代码放入 `src/pipeliner/`，测试放入 `tests/`，并保持与 OpenSpec 任务一一对应。

## Build, Test, and Development Commands
当前仓库没有可执行应用或正式构建流程；日常贡献主要围绕文档与规格校对。

- `rg --files "docs" "openspec"`：快速浏览仓库中的设计与规格文件。
- `rg -n "Requirement:|Scenario:" "openspec"`：检查规范性需求与场景定义。
- `git log --oneline`：查看提交历史；当前历史较短，便于保持提交主题清晰。

若新增 Python 代码，请统一使用 `uv` 作为入口，并在 README 或本文件补充实际命令，例如 `uv run pytest`。
建议新增实现后同步提供最小命令集，例如 `uv sync`、`uv run pytest`、`uv run ruff check .`、`uv run alembic upgrade head`。

## Coding Style & Naming Conventions
- Markdown 使用 ATX 标题（`#`、`##`），段落简洁，优先短句。
- 规格术语保持一致：使用 `workflow spec`、`artifact manifest`、`callback payload` 等既有命名。目录、文件与示例名优先体现业务语义，例如 `workflow-runtime`、`run-operations`。
- 新增 Python 代码时使用 4 空格缩进、类型标注和清晰模块边界；文件名采用 `snake_case`。
- 避免在 `docs/` 与 `openspec/` 中重复定义同一事实，文档应引用真源而非复制。

## Testing Guidelines
当前没有自动化测试套件。提交设计改动时，至少自检：

- 变更是否同步更新 `proposal.md`、`design.md`、`tasks.md` 或对应 `spec.md`。
- `Requirement` 与 `Scenario` 是否完整、无冲突、可验证。

若引入实现代码，请添加 `tests/test_*.py`，优先覆盖工作流校验、状态机流转、callback 幂等和 artifact 注册，并补一个端到端 MVP 用例。


## Architecture & Change Workflow
本仓库以 OpenSpec 变更流作为主线：先在 `openspec/changes/` 中写清 proposal、design、tasks，再推进实现或补充主规格。贡献时优先确认变更落点属于哪个子域，例如 workflow definition、runtime、callback reporting 或 artifact registry，避免跨文档随意扩散。

## Security & Configuration Tips
不要提交本地数据库、run 目录、大体积 artifact、导出的 payload 或任何密钥文件。`temp/` 中的内容默认按可丢弃资料处理；当其中信息需要长期保留时，应整理后迁移到 `docs/` 或 `openspec/`。

## Commit & Pull Request Guidelines
当前提交历史仅有 `first commit`，建议后续统一使用 **简短、祈使句、聚焦单一变更** 的提交标题，例如：`add workflow runtime spec`。

PR 应包含：变更目的、影响目录、关联的 `openspec/changes/...` 路径，以及必要的截图或示例输出（仅在涉及 UI 或 CLI 时提供）。若修改协议，请明确说明兼容性影响与迁移方式；避免把临时产物、数据库文件、运行输出或敏感配置提交到仓库。
