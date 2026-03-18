# Studio 使用说明

本指南描述仅通过 Studio 完成从创作、发布、运行、驱动到迭代的闭环流程，不依赖 CLI。

## 快速上手

1. 访问 `http://localhost:3000`，进入 Studio。
2. 在 `/authoring` 创建新的 authoring session，填写 Session Title 与 Intent Brief。
3. 在 Instruction 中描述需要修改或完善的内容：
   - 使用「保存草案」保存当前 spec。
   - 使用「继续会话」提交增量指令并生成新 revision。
   - 使用「Claude 生成」调用 Claude Code 生成新草案。
4. Lint 无阻塞后，点击「发布」生成 workflow version。
5. 在 `/workflows` 选择版本，点击「Start Run」并填写输入。
6. 在 `/runs/{run_id}` 查看 timeline、callbacks、artifacts 与 logs。
7. 使用「自动驱动」执行可调度节点，查看 stop reason 与步骤摘要。
8. 在 Artifact / Log 列表点击任一条目查看预览（超限会提示路径）。
9. 当 run 进入 attention 状态时，在 `/attention` 发起迭代，继续优化 workflow。

## 迭代入口

- 在 workflow 版本页点击「发起迭代」，基于该版本创建新的 authoring session。
- 在 attention 列表点击「发起迭代」，系统会带入 rework brief 与来源信息。

## 运行与调试

- Timeline 展示最新节点状态与 stop reason。
- Node Detail 可查看 callbacks、artifacts、log refs 与 raw context。
- Preview 面板支持 JSON/Text/目录预览，binary 会提示不可预览。
- 运行详情默认跟随当前焦点节点；手动切换历史轮次后会保持固定，直到点击“回到当前节点”。
- 当终端暂无输出时，页面会区分“排队中 / 已启动但无输出 / 慢启动告警 / 失败摘要”。

## 运行清理与队列维护

- `/runs` 按“需要处理 / 进行中 / 已完成与已停止”分组展示，优先处理 attention 项。
- 非运行中的 run 支持多选批量删除。
- 已结束 batch 支持多选批量删除；若关联 run 已删除，批次行会保留历史并标记为 deleted。

## Claude 诊断

- `/settings` 提供 Claude base URL、API host、proxy 摘要及来源信息。
- 若未检测到有效代理变量，页面会给出显式告警提示，便于优先排查网络/代理配置问题。

## 节点 Skill 与项目目录

每个 workflow 都对应 `projects/<workflow_id>/` 目录。保存草案、Claude 生成或迭代时，会为节点 executor/validator 创建或补齐 `.claude/skills/<skill>`，`SKILL.md` 仅在缺失时生成且不会覆盖手工编辑内容，`references/node_context.json` 在每次草案更新时同步节点上下文。运行期 executor/validator 在项目目录中执行，以确保技能自动发现。 
## 建议流程

- Intent Brief 描述目标、输入输出与验收标准。
- Instruction 描述要变更的具体内容。
- 每次修改后查看 lint 结果，避免发布阻塞。
- attention run 优先通过迭代修订 spec，再驱动 run。
