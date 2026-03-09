# Pipeliner Claude Validator Task

你是节点 validator。请读取上下文并生成判定结果。

- run_id: `run_20260309114830_48cadb22`
- node_id: `final_review`
- round_no: `1`
- validator_id: `final-gate`
- validator_skill: `approve-final-article`
- context_file: `/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner-real-claude-test/runs/mvp-review-loop/run_20260309114830_48cadb22/nodes/final_review/rounds/1/validators/final-gate.json`
- result_file: `/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner-real-claude-test/runs/mvp-review-loop/run_20260309114830_48cadb22/nodes/final_review/rounds/1/validators/final-gate.result.json`

必须写入 result_file，JSON 结构如下：
1. pass:
{"execution":{"status":"completed"},"verdict":{"status":"pass","summary":"...","target_artifacts":[]}}
2. revise:
{"execution":{"status":"completed"},"verdict":{"status":"revise","summary":"...","target_artifacts":[]},"rework_brief":{"must_fix":[{"target":"...","problem":"...","expected":"..."}],"preserve":[],"resubmit_instruction":"...","evidence":[]}}
3. blocked:
{"execution":{"status":"completed"},"verdict":{"status":"blocked","summary":"...","target_artifacts":[]}}
约束：
1. 不要改动任务目录之外的文件。
2. 只写入 result_file，不要调用 runtime API。
3. result_file 必须是合法 JSON。
