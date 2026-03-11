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

## 建议流程

- Intent Brief 描述目标、输入输出与验收标准。
- Instruction 描述要变更的具体内容。
- 每次修改后查看 lint 结果，避免发布阻塞。
- attention run 优先通过迭代修订 spec，再驱动 run。
