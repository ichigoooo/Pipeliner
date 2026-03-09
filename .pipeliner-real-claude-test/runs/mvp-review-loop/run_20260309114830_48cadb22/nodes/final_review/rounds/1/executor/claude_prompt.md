# Pipeliner Claude Executor Task

你是节点 executor。请读取上下文并产出交付物。

- run_id: `run_20260309114830_48cadb22`
- node_id: `final_review`
- round_no: `1`
- context_file: `/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner-real-claude-test/runs/mvp-review-loop/run_20260309114830_48cadb22/nodes/final_review/rounds/1/executor/context.json`

必须写入以下目标路径：
- artifact `approved_article@v1` => `/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner-real-claude-test/runs/mvp-review-loop/run_20260309114830_48cadb22/artifacts/approved_article@v1/payload/approved_article.md` (file)

约束：
1. 不要改动任务目录之外的文件。
2. 只要产物写入成功即可退出，回调由 orchestrator 自动处理。
