# Pipeliner：Artifact Manifest 设计文档

## 文档目的

本文档用于单独沉淀 `artifact manifest` 的 V1 设计，避免交付物协议继续堆叠到总设计文档与其他协议文档中。

本文档当前记录两类内容：

- 已确认设计：已经达成一致、可作为 V1 实施基础的部分。
- 待继续讨论：不阻塞 V1，但可能影响后续协议演进的部分。

---

## 一、角色定位（已确认）

在当前设计中，`artifact manifest` 的定位非常明确：

- 它是交付物在系统中的正式登记信息。
- 它负责让系统定位、验证、追踪一个交付物。
- 它不是 artifact payload 本体，也不是 verdict 或运行日志容器。
- 它服务于 Runtime、Validator 和下游节点对 artifact 的稳定引用与消费。

一句话概括：

> `artifact manifest` 是交付物的官方登记表，而不是档案袋。

---

## 二、设计目标（已确认）

当前确认，V1 的 `artifact manifest` 至少应满足以下目标：

### 1. 稳定标识一个交付物

- 系统必须知道这个 artifact 是谁。
- 系统必须知道它是哪一版。

### 2. 说明它从哪来

- 系统必须知道该 artifact 由哪个 `run`、哪个 `node`、哪一轮、哪个角色产出。

### 3. 说明它存在哪

- 系统必须能够通过 manifest 找到 artifact 的实际存储位置。
- V1 先以 `local_fs` 作为第一个存储后端。

### 4. 确认它没有被偷偷改动

- 系统必须有最小完整性信息。
- V1 中，`digest` 是关键字段。

### 5. 不让 manifest 膨胀成杂项容器

- manifest 只描述交付物事实。
- verdict、返工、日志、handoff 等不应塞进 manifest。

---

## 三、顶层设计原则（已确认）

### 1. Manifest 保持薄核心

当前确认：

- `manifest` 应只承载系统识别、定位、校验、追踪交付物所必需的信息。
- 不应承载与交付物无直接关系的运行态或语义态信息。

### 2. Callback 只传 artifact ref

当前确认：

- `node callback payload` 中只传递最小 artifact ref。
- Runtime 再通过 `artifact_id + version` 解析到对应 manifest。

### 3. 发布后不可变

当前确认：

- 一旦 artifact 发布并生成 manifest，对应版本即视为不可变。
- 返工应生成新版本，而不是原地修改旧版本。

### 4. V1 先支持 `local_fs`

当前确认：

- V1 中，`storage.backend` 先收敛为 `local_fs`。
- 字段设计仍为未来扩展对象存储或外部引用预留空间。

---

## 四、当前建议的顶层结构（已确认）

当前推荐的顶层结构如下：

```text
Artifact Manifest
├─ schema_version
├─ artifact_id
├─ version
├─ kind
├─ produced_by
├─ storage
├─ integrity
├─ created_at
├─ descriptor    (optional)
└─ lineage       (optional)
```

这套结构的设计意图如下：

- `schema_version`
  - 标识 manifest 自身遵循的协议版本。
- `artifact_id`
  - 标识交付物名字。
- `version`
  - 标识交付物版本。
- `kind`
  - 标识交付物形态。
- `produced_by`
  - 标识该 artifact 从哪来。
- `storage`
  - 标识该 artifact 存在哪。
- `integrity`
  - 提供最小完整性校验信息。
- `created_at`
  - 标识发布时间。
- `descriptor`
  - 作为轻量消费提示层。
- `lineage`
  - 作为轻量血缘层。

---

## 五、各字段职责与当前收敛版草案（已确认）

### 1. `schema_version`

职责：

- 标识 `artifact manifest` 自身的协议版本。

当前判断：

- 必需字段。

### 2. `artifact_id`

职责：

- 标识交付物的稳定名字。
- 应与 callback 中的 artifact ref 对齐。

当前判断：

- 必需字段。

### 3. `version`

职责：

- 标识交付物的明确版本。

当前判断：

- 必需字段。
- 当前建议保留简单版本表达，例如：`v1`、`v2`、`v3`。

这里进一步确认：

- 这里的 `version` 是 artifact 在一次 workflow run 中的运行内版本号，用于表达返工、重提或重新发布后的版本递增。
- 它不等同于 workflow spec 中 `metadata.version` 使用的语义化版本。
- callback payload 中引用 artifact 时，也应沿用这里的版本语义。

### 4. `kind`

职责：

- 描述已发布交付物的物理或组织形态。

当前判断：

- 必需字段。

当前建议的 V1 基础值为：

- `file`
- `directory`
- `collection`

这里进一步确认：

- `kind` 用于描述已发布 artifact 的实际形态。
- 它不等同于 `workflow spec` 中输入输出合同使用的 `shape`。
- `shape` 回答“下游期望接收到什么形态的接口”，`kind` 回答“这个 artifact 实际以什么物理或组织形态被发布”。
- 二者有关联，但不要求一一映射。
- 后续可以扩展 `inline`、`external` 等类型，但当前不阻塞 V1。

### 5. `produced_by`

职责：

- 标识该 artifact 由谁在什么上下文中产出。

当前收敛版最小子字段为：

- `run_id`
- `node_id`
- `round_no`
- `role`

例如：

```json
{
  "run_id": "run_20260308_xxx",
  "node_id": "draft_article",
  "round_no": 1,
  "role": "executor"
}
```

这里进一步确认：

- 当前大多数 artifact 会由 `executor` 产出。
- 保留 `role` 字段，可以为未来 validator 产出 artifact 的场景保留空间。

### 6. `storage`

职责：

- 标识该 artifact 的存储后端与定位方式。

当前收敛版最小子字段为：

- `backend`
- `uri`

当前建议：

- `backend` 的 V1 最小值为：
  - `local_fs`

这里进一步确认：

- 当 `backend = local_fs` 时，`uri` 应表达为相对 Pipeliner workspace 或 run root 约定基准的相对路径，不建议使用绝对路径。
- V1 当前不建议在 `uri` 中使用 `file://` scheme，而是统一使用普通路径字符串。
- 这样做的目的是让 artifact manifest 更容易在不同机器、不同工作目录之间迁移，而不把宿主机绝对路径硬编码进协议。

例如：

```json
{
  "backend": "local_fs",
  "uri": "runs/wechat-article-pipeline/run_20260308_xxx/artifacts/article_draft@v1/payload/article.md"
}
```

### 7. `integrity`

职责：

- 提供最小完整性校验信息。

当前收敛版最小子字段为：

- `digest`

当前推荐的可选附加字段为：

- `size_bytes`

这里进一步确认：

- `digest` 是 V1 的关键字段。
- 没有它，系统很难确认 validator 验的是不是同一个已发布版本。

### 8. `created_at`

职责：

- 标识该 artifact 版本的发布时间。

当前判断：

- 必需字段。

### 9. `descriptor`（可选）

职责：

- 作为轻量消费提示层。
- 改善下游消费体验，但不应进入核心必填集合。

当前推荐的可选子字段为：

- `media_type`
- `entrypoint`
- `index_file`
- `item_count`

这里进一步确认：

- `media_type` 让消费者快速理解内容类型。
- `entrypoint` 让消费者知道主入口是什么。
- `index_file` 对 `collection` 尤其重要。
- `item_count` 让系统和人类快速感知规模。

### 10. `lineage`（可选）

职责：

- 提供轻量血缘信息。

当前推荐的可选子字段为：

- `parent_artifacts`

例如：

```json
{
  "parent_artifacts": [
    {
      "artifact_id": "approved_topics",
      "version": "v1"
    }
  ]
}
```

这里进一步确认：

- V1 不建议做复杂血缘图谱。
- 先有最小父引用关系即可。

---

## 六、当前推荐的三个最小示例（已确认）

### 1. 单文件 Artifact

```json
{
  "schema_version": "pipeliner.artifact/v1alpha1",
  "artifact_id": "article_draft",
  "version": "v1",
  "kind": "file",
  "produced_by": {
    "run_id": "run_20260308_xxx",
    "node_id": "draft_article",
    "round_no": 1,
    "role": "executor"
  },
  "storage": {
    "backend": "local_fs",
    "uri": "runs/wechat-article-pipeline/run_20260308_xxx/artifacts/article_draft@v1/payload/article.md"
  },
  "integrity": {
    "digest": "sha256:..."
  },
  "created_at": "2026-03-08T16:00:00Z",
  "descriptor": {
    "media_type": "text/markdown",
    "entrypoint": "article.md"
  }
}
```

### 2. 目录型 Artifact

```json
{
  "schema_version": "pipeliner.artifact/v1alpha1",
  "artifact_id": "research_bundle",
  "version": "v1",
  "kind": "directory",
  "produced_by": {
    "run_id": "run_20260308_xxx",
    "node_id": "research_node",
    "round_no": 1,
    "role": "executor"
  },
  "storage": {
    "backend": "local_fs",
    "uri": "runs/research-pipeline/run_20260308_xxx/artifacts/research_bundle@v1/payload"
  },
  "integrity": {
    "digest": "sha256:..."
  },
  "created_at": "2026-03-08T16:00:00Z",
  "descriptor": {
    "entrypoint": "summary.md"
  }
}
```

### 3. 集合型 Artifact

```json
{
  "schema_version": "pipeliner.artifact/v1alpha1",
  "artifact_id": "article_batch",
  "version": "v3",
  "kind": "collection",
  "produced_by": {
    "run_id": "run_20260308_xxx",
    "node_id": "batch_generate",
    "round_no": 2,
    "role": "executor"
  },
  "storage": {
    "backend": "local_fs",
    "uri": "runs/content-pipeline/run_20260308_xxx/artifacts/article_batch@v3/payload"
  },
  "integrity": {
    "digest": "sha256:..."
  },
  "created_at": "2026-03-08T16:00:00Z",
  "descriptor": {
    "index_file": "index.json",
    "item_count": 12
  },
  "lineage": {
    "parent_artifacts": [
      {
        "artifact_id": "approved_topics",
        "version": "v1"
      }
    ]
  }
}
```

---

## 七、当前明确不属于 Artifact Manifest 的内容（已确认）

为了避免 `manifest` 膨胀，当前明确以下内容不应默认进入 `artifact manifest`：

- `verdict`
- `rework_brief`
- callback 历史
- 执行日志
- handoff 规则
- UI 展示字段
- 完整 validator 结果
- artifact payload 本体

这些对象都与 artifact 有关，但不属于交付物登记信息本身。

---

## 八、与其他协议的衔接补充（已确认）

### 1. 与 `workflow spec` 的关系

当前补充确认：

- `workflow spec` 中的 `shape` 定义的是节点或工作流输出合同。
- 当某个输出真正被节点发布并进入流转时，Runtime 应为其登记对应的 artifact manifest。
- 因此，`workflow spec` 负责声明交付接口，artifact manifest 负责登记实际交付物。

### 2. 与 `node callback payload` 的关系

当前补充确认：

- callback payload 中的 artifact ref 使用 `{ artifact_id, version }` 指向 manifest。
- Runtime 收到 callback 后，应能用这组引用解析到对应 manifest，而不是直接依赖 payload 本体内容。

### 3. 最小失败语义

当前补充确认：

- 若 artifact payload 已生成但 manifest 登记失败，Runtime 应将该次产物发布视为失败，而不是假定发布成功。
- 若由于存储或登记失败导致后续节点无法解析 artifact ref，应把问题提升为运行层失败或人工介入，而不是让下游带着不完整引用继续工作。
- V1 当前不进一步设计复杂恢复框架，但至少要保证失败不会被静默吞掉。

---

## 九、V1 当前结论（已确认）

当前确认的 V1 结论为：

- 必需字段：
  - `schema_version`
  - `artifact_id`
  - `version`
  - `kind`
  - `produced_by`
  - `storage`
  - `integrity.digest`
  - `created_at`
- 可选字段：
  - `descriptor`
  - `lineage`
- `storage.backend` 的 V1 最小值先收敛为：
  - `local_fs`
- `kind` 的 V1 基础值先收敛为：
  - `file`
  - `directory`
  - `collection`

---

## 十、待继续讨论的内容

在 V1 方向已经确认的前提下，后续仍可继续讨论：

### 1. `kind` 是否需要扩展更多基础值

例如：

- 是否需要 `inline`
- 是否需要 `external`

### 2. `storage` 是否需要更多定位字段

例如：

- 是否需要 `manifest_uri`
- 是否需要区分路径与对象键

### 3. `descriptor` 的未来扩展边界

例如：

- 是否需要更多轻量消费提示
- 如何避免 `descriptor` 重新变胖

这些问题当前都不阻塞 V1 实施。

---

## 十一、协议演进与兼容性约定（已确认）

当前补充以下跨版本规则，供 `artifact manifest` 使用：

- `schema_version` 的主版本升级表示不兼容变更，需要显式迁移。
- `schema_version` 的次版本升级表示向后兼容的扩展，例如新增可选字段。
- 补丁级修订用于文档澄清或不改变协议含义的修正。
- Runtime 在 V1 中至少应拒绝自己无法识别主版本的 manifest，而不是静默按旧格式解析。

---

## 十二、当前结论

截至目前，`artifact manifest` 可以被概括为：

> 一份面向系统的交付物登记协议。
>
> 它负责让 Runtime、Validator 和下游节点稳定定位、验证和追踪交付物。
>
> 它不承载 verdict、返工、日志和展示职责。

更简洁地说：

```text
artifact manifest = canonical artifact registration
```
