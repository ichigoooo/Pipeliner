# Pipeliner：Node Callback Payload 设计文档

## 文档目的

本文档用于单独沉淀 `node callback payload` 的 V1 设计，避免运行时协议继续堆叠到总设计文档和 `workflow spec` 文档中。

本文档当前记录两类内容：

- 已确认设计：已经达成一致、可作为 V1 实施基础的部分。
- 待继续讨论：不阻塞 V1，但可能影响后续协议演进的部分。

---

## 一、角色定位（已确认）

在当前设计中，`node callback payload` 的定位非常明确：

- 它是节点角色向 Runtime 回报执行结果的最小协议对象。
- 它服务于 Runtime 的接收、记录、转发和流程推进。
- 它不是 artifact 内容容器，不直接承载大文件本体。
- 它不是运行日志，也不是最终审计报表。

一句话概括：

> `node callback payload` 是 Runtime 用来接住节点结果并驱动流转的协议外壳。

---

## 二、设计目标（已确认）

当前确认，V1 的 `node callback payload` 至少应满足以下目标：

### 1. 让 Runtime 能可靠定位上下文

- Runtime 必须能够知道这条回调属于哪个 `run`、哪个 `node`、哪个 `round`。
- Runtime 还必须知道当前回调来自哪个角色。

### 2. 区分运行状态与语义结论

- 运行失败、超时，与“内容不合格”不是一回事。
- 协议层必须明确区分这两类信息。

### 3. 只传递 artifact 引用，不传递大文件本体

- 回调中只提交 artifact 引用。
- 真正的 payload 通过 artifact manifest 与存储位置解析。

### 4. 同时支持 Executor 与 Validator

- `executor` 和 `validator` 应共用同一套顶层协议外壳。
- 通过角色字段和局部必填规则区分不同回调形态。

### 5. 支撑返工闭环

- `validator` 需要能够返回 `pass / revise / blocked`。
- 在 `revise` 时，需要附带可执行的返工单。

---

## 三、顶层设计原则（已确认）

### 1. 协议保持薄，而不是成为大杂烩

当前确认：

- `callback payload` 只承载 Runtime 推进流程所必需的信息。
- 不应把 manifest 本体、执行日志、UI 展示信息、完整 artifact 明细等全部塞进来。

### 2. 顶层结构统一，角色语义分流

当前确认：

- `executor` 和 `validator` 共享同一套顶层结构。
- 通过 `actor.role` 与局部字段约束，区分不同角色的提交内容。

### 3. artifact 只以最小引用进入回调

当前确认：

- V1 中，artifact 在 callback 内只以最小引用出现。
- 当前建议的最小 artifact ref 为：
  - `artifact_id`
  - `version`

### 4. V1 优先保证闭环，不提前复杂化

当前确认：

- V1 不提前引入复杂状态机字段。
- V1 不提前引入复杂批量 verdict 结构。
- V1 先确保 `executor -> validator -> executor/downstream` 的闭环成立。

---

## 四、当前建议的顶层结构（已确认）

当前推荐的顶层结构如下：

```text
Node Callback Payload
├─ schema_version
├─ event_id
├─ sent_at
├─ run_id
├─ node_id
├─ round_no
├─ actor
├─ execution
├─ submission
├─ verdict
└─ rework_brief
```

这套结构的设计意图如下：

- `schema_version`
  - 标识这份 callback 自己遵循的协议版本。
- `event_id`
  - 作为幂等键，帮助 Runtime 去重。
- `sent_at`
  - 记录回调生成时间。
- `run_id / node_id / round_no`
  - 定位当前流程上下文。
- `actor`
  - 标识回调来自哪个角色。
- `execution`
  - 承载运行层状态。
- `submission`
  - 承载 executor 提交的 artifact 引用。
- `verdict`
  - 承载 validator 的语义验收结论。
- `rework_brief`
  - 承载 validator 返回的返工单。

---

## 五、各字段职责与当前收敛版草案（已确认）

### 1. `schema_version`

职责：

- 标识 callback payload 自身的协议版本。

当前判断：

- 必需字段。

### 2. `event_id`

职责：

- 作为事件级唯一标识。
- 用于 Runtime 做幂等去重。

当前判断：

- 必需字段。

### 3. `sent_at`

职责：

- 标识本次回调的发送时间。

当前判断：

- 必需字段。

### 4. `run_id / node_id / round_no`

职责：

- 共同定位当前回调属于哪个工作流运行、哪个节点、哪一轮。

当前判断：

- 均为必需字段。

### 5. `actor`

职责：

- 标识回调来自哪个角色。

当前收敛版最小子字段为：

- `role`
- `validator_id`（仅 validator 角色时需要）

当前建议：

- `role` 取值：
  - `executor`
  - `validator`

例如：

```json
{
  "role": "validator",
  "validator_id": "content-review"
}
```

### 6. `execution`

职责：

- 承载运行层状态，而不是语义验收结论。

当前收敛版最小子字段为：

- `status`
- `message`（可选）

当前建议 `status` 的 V1 取值为：

- `completed`
- `failed`
- `timeout`

这里进一步确认：

- `completed` 表示角色本次运行完成并成功提交回调。
- `failed` 表示角色执行失败。
- `timeout` 表示角色执行超时。

### 7. `submission`

职责：

- 承载 executor 提交的 artifact 引用集合。

当前收敛版最小子字段为：

- `artifacts`

其中每个 artifact ref 当前建议最小字段为：

- `artifact_id`
- `version`

例如：

```json
{
  "artifacts": [
    {
      "artifact_id": "article_draft",
      "version": "v1"
    },
    {
      "artifact_id": "draft_meta",
      "version": "v1"
    }
  ]
}
```

这里进一步确认：

- `submission` 主要服务于 executor 回调。
- V1 不建议在这里塞入 manifest 本体或 artifact 内容。

### 8. `verdict`

职责：

- 承载 validator 的语义验收结论。

当前收敛版最小子字段为：

- `status`
- `target_artifacts`
- `summary`

当前建议 `status` 的 V1 取值为：

- `pass`
- `revise`
- `blocked`

例如：

```json
{
  "status": "revise",
  "target_artifacts": [
    {
      "artifact_id": "article_draft",
      "version": "v1"
    }
  ],
  "summary": "标题吸引力不足，第二部分论证不完整"
}
```

### 9. `rework_brief`

职责：

- 承载 validator 在 `revise` 场景下返回给 executor 的返工单。

当前收敛版最小子字段为：

- `must_fix`
- `preserve`
- `resubmit_instruction`
- `evidence`（可选）

这里进一步确认：

- 当 `verdict.status = revise` 时，`rework_brief.must_fix` 必须存在，且不能为空数组。
- 若 `must_fix` 缺失，或虽然存在但为空数组，应视为无效的 validator payload，而不是将其等同于 `pass`。
- 这样做的目的是保证“返工”总能携带明确、可执行的修改要求。

例如：

```json
{
  "must_fix": [
    {
      "target": "标题",
      "problem": "吸引力不足",
      "expected": "更明确呈现读者收益"
    },
    {
      "target": "第二部分",
      "problem": "论证跳跃",
      "expected": "补足过渡与论证"
    }
  ],
  "preserve": [
    "保持整体口语化风格",
    "保留案例段落核心事实"
  ],
  "resubmit_instruction": "重新提交完整文案初稿",
  "evidence": [
    "第二部分从问题直接跳到结论"
  ]
}
```

---

## 六、V1 角色约束（已确认）

### 1. 当 `actor.role = executor`

当前确认：

- 必须有：
  - `execution`
  - `submission`
- 不应有：
  - `verdict`
  - `rework_brief`

### 2. 当 `actor.role = validator`

当前确认：

- 必须有：
  - `execution`
  - `verdict`
- 当 `verdict.status = revise` 时：
  - 必须有 `rework_brief`
  - `rework_brief.must_fix` 必须非空
- 当 `verdict.status = pass` 时：
  - `rework_brief` 应为空
- 当 `verdict.status = blocked` 时：
  - `rework_brief` 可为空，但建议提供阻塞原因

---

## 七、与其他协议的衔接补充（已确认）

### 1. 与 `artifact manifest` 的关系

当前补充确认：

- `submission.artifacts[]` 与 `verdict.target_artifacts[]` 中出现的 `{ artifact_id, version }`，引用的都是已经或即将被 Runtime 登记的 artifact 身份。
- 其中 `version` 的语义应与 `docs/artifact-manifest-design.md` 中的 artifact 版本保持一致，使用运行内版本号表达，例如 `v1`、`v2`。
- 它不等同于 workflow 自身的语义化版本。

### 2. 最小幂等语义

当前补充确认：

- callback 事件应以 `event_id` 作为幂等键。
- 若同一 `event_id` 被重复提交，Runtime 应将其视为同一事件的重放，而不是重复推进流程。
- V1 当前不进一步设计复杂重试协议，但至少要保证重复 callback 不会造成重复放行。

### 3. 与 `runtime guards` 的关系

当前补充确认：

- 若 Runtime 在 `timeout` 边界前未收到预期 callback，应按 `docs/runtime-guards-design.md` 中的规则把该次执行记为 `timeout`。
- callback 协议负责表达“收到了什么”，runtime guards 负责表达“多久没收到就判定超时”。

---

## 八、当前推荐的两个最小示例（已确认）

### 1. Executor 完成回调

```json
{
  "schema_version": "pipeliner.callback/v1alpha1",
  "event_id": "evt_exec_001",
  "sent_at": "2026-03-08T16:00:00Z",
  "run_id": "run_20260308_xxx",
  "node_id": "draft_article",
  "round_no": 1,
  "actor": {
    "role": "executor"
  },
  "execution": {
    "status": "completed"
  },
  "submission": {
    "artifacts": [
      {
        "artifact_id": "article_draft",
        "version": "v1"
      },
      {
        "artifact_id": "draft_meta",
        "version": "v1"
      }
    ]
  },
  "verdict": null,
  "rework_brief": null
}
```

### 2. Validator 打回回调

```json
{
  "schema_version": "pipeliner.callback/v1alpha1",
  "event_id": "evt_val_001",
  "sent_at": "2026-03-08T16:05:00Z",
  "run_id": "run_20260308_xxx",
  "node_id": "draft_article",
  "round_no": 1,
  "actor": {
    "role": "validator",
    "validator_id": "content-review"
  },
  "execution": {
    "status": "completed"
  },
  "submission": null,
  "verdict": {
    "status": "revise",
    "target_artifacts": [
      {
        "artifact_id": "article_draft",
        "version": "v1"
      }
    ],
    "summary": "标题吸引力不足，第二部分论证不完整"
  },
  "rework_brief": {
    "must_fix": [
      {
        "target": "标题",
        "problem": "吸引力不足",
        "expected": "明确表达读者收益"
      },
      {
        "target": "第二部分",
        "problem": "论证跳跃",
        "expected": "补足过渡与论证"
      }
    ],
    "preserve": [
      "保持整体口语化风格",
      "保留案例段落核心事实"
    ],
    "resubmit_instruction": "重新提交完整文案初稿",
    "evidence": [
      "第二部分从问题直接跳到结论"
    ]
  }
}
```

---

## 八、当前明确不属于 Callback Payload 的内容（已确认）

为了避免协议膨胀，当前明确以下内容不应默认进入 `callback payload`：

- artifact payload 本体
- artifact manifest 本体
- 完整执行日志
- UI 展示字段
- Runtime 聚合状态
- 节点历史 verdict 列表
- 下游节点计划信息

这些对象与节点回调有关，但不属于 V1 callback 协议本身。

---

## 九、待继续讨论的内容

在 V1 方向已经确认的前提下，后续仍可继续讨论：

### 1. 运行失败细分是否需要更多状态

例如：

- 是否需要区分 `cancelled`。
- 是否需要区分脚本失败与模型失败。

### 2. Artifact Ref 是否需要补充更多字段

例如：

- 是否需要 `manifest_uri`。
- 是否需要 `kind` 或 `shape`。

### 3. Validator Verdict 的未来扩展

例如：

- 是否需要标签化理由。
- 是否需要风险等级或分数制。

这些问题当前都不阻塞 V1 实施。

---

## 十、协议演进与兼容性约定（已确认）

当前补充以下跨版本规则，供 `node callback payload` 使用：

- `schema_version` 的主版本升级表示不兼容变更，需要显式迁移。
- `schema_version` 的次版本升级表示向后兼容的扩展，例如新增可选字段。
- 补丁级修订用于文档澄清或不改变协议含义的修正。
- Runtime 在 V1 中至少应拒绝自己无法识别主版本的 callback payload，而不是带着猜测继续推进。

---

## 十一、当前结论

截至目前，`node callback payload` 可以被概括为：

> 一份面向 Runtime 的节点回调协议外壳。
>
> 它负责让 Runtime 准确接收节点执行结果、区分运行状态与语义结论、接住 artifact 引用，并支撑 validator 返工闭环。
>
> 它不承载大文件本体，不承担日志和展示职责。

更简洁地说：

```text
node callback payload = runtime-facing result envelope
```
