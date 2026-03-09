# Pipeliner Claude Executor Task

你是节点 executor。请读取上下文并产出交付物。

- run_id: `run_20260309112003_74dfce61`
- node_id: `draft_article`
- round_no: `1`
- context_file: `/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner-real-claude-test/runs/mvp-review-loop/run_20260309112003_74dfce61/nodes/draft_article/rounds/1/executor/context.json`

必须写入以下目标路径：
- artifact `article_draft@v1` => `/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner-real-claude-test/runs/mvp-review-loop/run_20260309112003_74dfce61/artifacts/article_draft@v1/payload/article_draft.md` (file)

约束：
1. 不要改动任务目录之外的文件。
2. 只要产物写入成功即可退出，回调由 orchestrator 自动处理。
