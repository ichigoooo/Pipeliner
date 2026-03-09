# Pipeliner：Runtime Guards 设计文档

## 文档目的

本文档用于单独沉淀 `runtime guards` 的 V1 设计，避免运行时护栏继续混杂在总设计文档和协议文档中。

本文档当前记录两类内容：

- 已确认设计：已经达成一致、可作为 V1 实施基础的部分。
- 待继续讨论：不阻塞 V1，但可能影响后续运行时演进的部分。

---

## 一、角色定位（已确认）

在当前设计中，`runtime guards` 的定位非常明确：

- 它们是 Runtime 在推进节点流转时使用的最小护栏规则。
- 它们不负责语义判断。
- 它们负责在超时、返工过多、阻塞和执行失败等情况下，阻止系统无限自动推进。

一句话概括：

> `runtime guards` 是 Runtime 的最小安全边界，而不是语义裁判器。

---

## 二、设计目标（已确认）

当前确认，V1 的 `runtime guards` 至少应满足以下目标：

### 1. 防止节点无限等待

- 某个角色长时间没有完成时，系统不能无限挂起。
- 必须有超时边界。

### 2. 防止节点无限返工

- `validator` 可以要求返工。
- 但节点不能无限循环在 `executor -> validator -> revise` 中。

### 3. 明确阻塞态的去向

- `blocked` 不是普通失败。
- 一旦进入 `blocked`，系统应停在待人工介入状态，而不是继续自动尝试。

### 4. 区分运行失败与语义不通过

- `failed / timeout` 属于运行层问题。
- `revise / blocked` 属于语义层问题。
- 护栏需要围绕运行层推进，而不是混淆这两层。

---

## 三、V1 当前收敛范围（已确认）

当前确认，V1 只收敛 4 个最小护栏：

- `timeout`
- `max_rework_rounds`
- `blocked_requires_manual`
- `failure_requires_manual`

这意味着：

- V1 暂不讨论更细的重试策略。
- V1 暂不讨论复杂的节点暂停/恢复编排细节。
- V1 先把“别无限跑、别无限等、别无限返工”这条底线立住。

---

## 四、各护栏的职责与当前建议（已确认）

### 1. `timeout`

职责：

- 约束节点角色执行的最大等待时间。

当前建议：

- 当某个角色在规定时间内未完成回调时，Runtime 将该次执行记为 `timeout`。
- `timeout` 属于运行层状态，而不是语义层 verdict。
- V1 中，`timeout` 后不自动做复杂恢复；是否进入人工介入，由 `failure_requires_manual` 配合决定。

当前设计意图：

- 先让系统明确知道“等太久了”。
- 不在 V1 里引入复杂的自动重试状态机。

### 2. `max_rework_rounds`

职责：

- 限制一个节点允许进入多少轮返工。

当前建议：

- 每当 validator 返回 `revise` 并进入下一轮重新提交时，`round_no` 递增。
- 当某节点返工轮次超过 `max_rework_rounds` 时，Runtime 不再自动继续推进。
- 超限后节点进入待人工介入状态。

当前设计意图：

- 避免节点陷入无穷返工。
- 让“自动化失败，需要人工接手”的边界清晰可见。

### 3. `blocked_requires_manual`

职责：

- 规定当 validator 给出 `blocked` 时，系统是否必须停到人工介入状态。

当前建议：

- V1 直接固定为：`true`。
- 一旦 validator 返回 `blocked`，Runtime 将节点标记为待人工介入，不再自动继续。

当前设计意图：

- `blocked` 本身就意味着缺少前提、约束冲突或需要人工判断。
- 因此 V1 不建议为 `blocked` 设计自动化恢复路径。

### 4. `failure_requires_manual`

职责：

- 规定当角色执行失败或超时达到护栏边界时，系统是否转入人工介入状态。

当前建议：

- V1 直接固定为：`true`。
- 当角色发生 `failed` 或 `timeout` 且超出系统允许范围时，节点进入待人工介入状态。

当前设计意图：

- V1 不追求复杂重试机制。
- 优先保证系统不会在未知失败状态下继续盲目自动推进。

---

## 五、V1 推荐的最小表达（已确认）

当前建议，V1 可以把这组护栏表达为一个非常薄的运行时配置对象：

```json
{
  "timeout": "30m",
  "max_rework_rounds": 3,
  "blocked_requires_manual": true,
  "failure_requires_manual": true
}
```

这里的设计意图是：

- `timeout` 明确等待边界。
- `max_rework_rounds` 明确返工边界。
- `blocked_requires_manual` 明确语义阻塞边界。
- `failure_requires_manual` 明确运行失败边界。

---

## 六、与现有协议的关系（已确认）

### 1. 与 `node callback payload` 的关系

当前确认：

- `execution.status = timeout / failed` 由 callback 协议表达运行层结果。
- `verdict.status = revise / blocked / pass` 由 callback 协议表达语义层结果。
- `runtime guards` 不新增新的 verdict 类型，而是决定 Runtime 在接到这些结果后如何停下或继续。

### 2. 与 `workflow spec` 的关系

当前确认：

- `runtime guards` 可以在未来进入 `workflow spec.defaults` 或节点级配置中。
- 但在当前阶段，先只把它们作为 V1 最小运行护栏设计确认下来。
- 是否进入 `defaults`，属于后续实现层和 spec 细化问题。

### 3. 与 Runtime 状态机的关系

当前确认：

- `runtime guards` 负责定义何时停止自动推进。
- 它们不负责定义完整 Runtime 状态机。
- V1 先只需保证在边界情况进入“待人工介入”这一稳定停点。

---

## 七、当前明确不进入 V1 的内容（已确认）

为了保持 V1 克制，当前明确以下内容不在本轮设计范围内：

- 自动重试次数的复杂分层
- 不同失败类型的差异化恢复策略
- 自动恢复 `blocked` 的流程
- 节点级暂停/恢复命令设计
- 人工介入后的恢复协议细节

这些问题后续都可以继续设计，但当前不阻塞进入实施。

---

## 八、当前结论

截至目前，`runtime guards` 可以被概括为：

> 一组由 Runtime 使用的最小运行护栏。
>
> 它们负责限制等待时间、返工轮次，并在阻塞或失败超过边界时把系统稳定停在待人工介入状态。
>
> 它们不负责语义判断，也不承担完整状态机设计。

更简洁地说：

```text
runtime guards = minimal runtime safety rails
```
