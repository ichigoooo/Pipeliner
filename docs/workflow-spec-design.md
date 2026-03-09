# Pipeliner：Workflow Spec 设计文档

## 文档目的

本文档用于单独沉淀 `workflow spec` 的设计目标、边界和当前已确认的顶层结构，避免这些内容继续堆叠在总设计文档中，导致主文档失焦。

本文档当前只记录两类内容：

- 已确认设计：已经达成一致、可作为后续细化基础的部分。
- 待继续讨论：顶层方向已收敛，但子字段和细节尚未定稿的部分。

---

## 一、Workflow Spec 的角色定位（已确认）

在当前设计中，`workflow spec` 的定位非常明确：

- 它是工作流在系统内部的唯一真源（canonical source）。
- 它描述的是“这个工作流应该是什么”，而不是“这个工作流已经跑成了什么样”。
- 它是 `Claude Code` 在 Authoring 阶段最终必须落下来的机器可读结构。
- 它也是 Runtime 在启动一次 Workflow Run 时进行快照锁定的基础对象。

这意味着：

- `workflow.view`、图结构视图、`Node Card` 等，都应从 `workflow spec` 派生。
- 用户可以通过更友好的视图理解和编辑工作流。
- 但系统内部最终仍应围绕 `workflow spec` 运作。

一句话概括：

> `workflow spec` 是工作流定义的机器真源，而不是运行结果容器，也不是 UI 展示对象本身。

---

## 二、Workflow Spec 的设计目标（已确认）

当前确认，`workflow spec` 的设计至少要同时满足以下目标：

### 1. 成为唯一真源

- 系统内部必须有一个唯一可信的工作流定义对象。
- `workflow spec` 应承担这个角色。
- 其他视图与说明文件，不应与之竞争“谁才是真相”。

### 2. 让 Runtime 可执行

- `workflow spec` 必须足够机器可读。
- Runtime 应能据此识别节点、依赖、输入输出、Skill 绑定、验收门和交接方式。

### 3. 让 Authoring 可约束

- `Claude Code` 生成工作流时，最终必须落到稳定结构上。
- 这样才能进行 Schema 校验、Lint 校验和返工修正。

### 4. 让技术用户仍可直接理解和修改

- 虽然它是机器真源，但不应被设计成过度反人类的结构。
- 目标用户仍是有一定技术背景的用户，因此应保留直接阅读和编辑底层 spec 的能力。

### 5. 严格区分设计态与运行态

- `workflow spec` 只定义工作流结构与合同。
- 它不应混入运行期状态、日志、回调历史、round 结果和 artifact 实体内容。

### 6. 为快照、回放与版本化提供基础

- 一次 Workflow Run 启动时，应能对 `workflow spec` 进行快照锁定。
- 后续回放、审计、排障时，应能明确知道当时运行的是哪一版定义。

一句话概括：

> `workflow spec` 的目标，是做一份既能被机器执行、又能被技术用户理解、还能被 Authoring 与 Lint 稳定约束的工作流真源。

---

## 三、Workflow Spec 的顶层设计原则（已确认）

### 1. 顶层只放“工作流作为合同”必需的信息

当前确认：

- 顶层字段应只承载工作流定义必需的设计态信息。
- 不应因为未来可能有用，就把运行态、UI 细节或其他侧向对象全部塞进来。

这意味着顶层主要应回答：

- 这份 spec 属于哪一版 schema。
- 这个 workflow 是谁。
- 这个 workflow 对外需要什么输入。
- 这个 workflow 对外承诺什么输出。
- 这个 workflow 由哪些节点及其依赖构成。

### 2. 依赖关系应尽量避免双真源

当前建议：

- 节点之间的关系，优先通过 `node.depends_on` 表达。
- V1 不建议在顶层再单独维护一份 `edges` 结构。

这样做的原因是：

- 能避免同时维护 `nodes` 与 `edges` 两份依赖真相。
- 更方便 Authoring、Lint 和 `Node Card` 派生。
- 也更符合“节点合同网络”这一建模方式。

### 3. Skill 只被引用，不被重新定义

当前确认：

- `workflow spec` 可以记录节点绑定了哪个 `Skill`。
- 但 `workflow spec` 不负责重新定义 `Skill` 的内部规范。
- `Skill` 的组织方式、内部资源和使用约定，应遵循既有 Skill 体系。

### 4. Workflow Spec 不承载运行结果

当前确认，以下内容不应进入 `workflow spec` 顶层：

- run id
- callback 历史
- validator verdict 历史
- round 结果
- artifact 实体内容
- 运行日志
- UI 渲染状态

这些内容属于运行态、调试态或视图层对象，不属于工作流定义本身。

---

## 四、当前建议的顶层结构（已确认）

当前推荐的顶层结构如下：

```text
Workflow Spec
├─ schema_version
├─ metadata
├─ inputs
├─ outputs
├─ nodes
├─ defaults      (optional)
└─ extensions    (optional)
```

这套结构的设计意图如下：

- `schema_version`
  - 标识这份 spec 自己遵循的 schema 版本。
- `metadata`
  - 标识这个 workflow 是谁，以及它的高层描述信息。
- `inputs`
  - 描述 workflow 从外部世界读取什么。
- `outputs`
  - 描述 workflow 最终对外承诺交付什么。
- `nodes`
  - 描述内部节点合同网络，是整个 spec 的核心部分。
- `defaults`
  - 提供工作流级默认值，作为节点级省略配置的补充。
- `extensions`
  - 作为未来扩展入口，避免后续每增加一点能力就重塑顶层结构。

---

## 五、当前建议的最小必需顶层字段（已确认）

如果按“先薄后厚”的设计原则进一步收敛，当前认为最小必需顶层字段可以只有：

- `schema_version`
- `metadata`
- `inputs`
- `outputs`
- `nodes`

换句话说：

```text
最小可用 Workflow Spec
= 身份 + 对外合同 + 内部节点网络
```

而以下字段当前更适合作为可选层：

- `defaults`
- `extensions`

这意味着：

- V1 不必过早在顶层预埋过多默认值和扩展结构。
- 但应为后续演进保留合理的放置位置。

---

## 六、各顶层字段的当前职责边界（已确认）

### 1. `schema_version`

职责：

- 标识这份 `workflow spec` 自己遵循的 schema 版本。
- 为后续 schema 演进、兼容和迁移提供依据。

当前判断：

- 这是必需字段。

### 2. `metadata`

职责：

- 承载工作流身份信息与高层语义说明。
- 帮助系统与技术用户识别这份工作流定义。

当前判断：

- 这是必需字段。
- 当前已确认采用一版偏薄的最小字段集合。

当前收敛版最小子字段为：

- `workflow_id`
- `title`
- `purpose`
- `version`

当前推荐但可选的附加字段为：

- `tags`

这里进一步确认：

- `workflow_id` 用于机器稳定标识。
- `title` 用于人类阅读。
- `purpose` 用于说明该 workflow 为什么存在。
- `version` 在当前阶段就应纳入，是工作流定义本身的重要版本锚点。
- `tags` 可用于分类与检索，但当前不应视为必需。

### 3. `inputs`

职责：

- 表达这个 workflow 从外部世界需要读取哪些输入。
- 它定义的是工作流级输入合同，而不是某个节点的局部输入。

当前判断：

- 这是必需字段。
- 当前已确认采用一版偏薄的最小字段集合。

当前收敛版最小子字段为：

- `name`
- `shape`
- `required`
- `summary`

这里进一步确认：

- `name` 用于在 workflow 内部稳定引用该输入。
- `shape` 用于表达输入合同层的期望形态，当前沿用前述开放式基础类型思路。
- `required` 应显式表达，而不依赖隐式默认值。
- `summary` 用一句人类可理解的话说明该输入的用途。
- 由于这是 workflow 级输入，因此当前不建议为其再设计 `from` 字段。
- 这里的 `shape` 属于节点或工作流合同层描述，不等同于 artifact manifest 中的 `kind`；`kind` 用于表达 artifact 发布后的物理或组织形态，见 `docs/artifact-manifest-design.md`。

### 4. `outputs`

职责：

- 表达这个 workflow 最终对外承诺交付哪些结果。
- 它定义的是工作流级输出边界，而不是每个节点自己的局部输出。

当前判断：

- 这是必需字段。
- 当前已确认采用一版偏薄的最小字段集合。

当前收敛版最小子字段为：

- `name`
- `from`
- `shape`
- `required`
- `summary`

这里进一步确认：

- `name` 用于标识 workflow 对外暴露的输出名。
- `from` 用于显式绑定该输出来自哪个内部节点的哪个输出结果。
- `shape` 用于表达输出合同层的期望形态。
- `required` 用于区分必交付结果与附带结果。
- `summary` 用于用一行话说明该输出的交付意义。
- 这里的 `shape` 仅表达交付接口希望呈现的形态，不直接决定底层 artifact 应以 `file`、`directory` 还是 `collection` 发布；后者由 artifact manifest 的 `kind` 表达。

其中，`from` 当前建议采用结构化对象表达，而不是拼接字符串。例如：

```json
{
  "node_id": "final_review",
  "output": "approved_article"
}
```

### 5. `nodes`

职责：

- 承载内部节点合同网络，是 `workflow spec` 的核心。
- 每个节点自身进一步定义输入、输出、角色、验收和交接。

当前判断：

- 这是必需字段。
- 当前已确认采用一版偏薄的节点合同结构。
- 当前建议使用节点数组承载，并通过每个节点内部的 `depends_on` 表达依赖关系。
- V1 不建议顶层额外维护一份独立 `edges`。

这里进一步确认：

- `node` 在 `workflow spec` 中，应被建模为“节点合同对象”，而不是“节点运行对象”。
- 它定义节点应读取什么、交付什么、由谁执行、由谁验收、怎样算通过、通过后如何交接。
- 它不应记录运行轮次、最新 verdict、callback 历史、artifact 实际路径或日志。

当前收敛版最小子字段为：

- `node_id`
- `title`
- `purpose`
- `archetype`
- `depends_on`
- `inputs`
- `outputs`
- `executor`
- `validators`
- `acceptance`
- `gate`
- `handoff`

#### 5.1 身份字段

当前确认：

- `node_id`：节点的稳定机器标识。
- `title`：给人阅读的短标题。
- `purpose`：一两句话说明该节点为什么存在。
- `archetype`：节点原型名，当前建议保留为必填；若不匹配预置原型，可使用 `custom`。

这里进一步确认：

- `archetype` 在 V1 中主要服务于作者理解、节点归类与生成工作流时的提示，不应用作 Runtime 的强行为开关。
- 当前不把 `archetype` 设计成严格闭集枚举；更合理的做法是提供推荐示例集，例如：`draft-content`、`review-content`、`generate-json`、`structured-extract`、`custom`。
- 也就是说，Runtime 应依赖节点合同本身，而不是依赖某个原型名隐式推断行为。

#### 5.2 依赖字段

当前确认：

- `depends_on` 用于表达该节点依赖哪些上游节点。
- 当前建议使用节点 id 数组，例如：

```json
["select_topics", "load_brand_rules"]
```

这里进一步确认：

- `depends_on` 提供节点依赖概览，便于阅读、画图与 review。
- 节点级 `inputs.from` 则提供更细的输入来源绑定。
- 二者允许存在一定冗余，但后续应通过 lint 检查其一致性。

当前建议补充 V1 最小 lint 规则：

- `[ERROR]` 若某个 `inputs.from.kind = node_output` 引用了上游节点，则该上游节点必须出现在当前节点的 `depends_on` 中。
- `[WARNING]` 若 `depends_on` 声明了某个上游节点，但当前节点没有任何 `inputs.from` 实际引用它，应提示作者确认该依赖是否多余。
- `[ERROR]` `depends_on` 中不得出现未知节点 id。
- `[ERROR]` 工作流依赖图不得形成循环依赖。
- 当 `depends_on` 与 `inputs.from` 冲突时，应以更细粒度的 `inputs.from` 作为事实来源，并将 `depends_on` 不一致视为 lint 错误，而不是运行时猜测修正。

#### 5.3 节点级 `inputs`

当前收敛版最小子字段为：

- `name`
- `from`
- `shape`
- `required`
- `summary`

当前建议 `from` 使用结构化对象表达，至少支持：

- `workflow_input`
- `node_output`

例如：

```json
{
  "name": "approved_topics",
  "from": {
    "kind": "node_output",
    "node_id": "select_topics",
    "output": "approved_topics"
  },
  "shape": "json",
  "required": true,
  "summary": "上游筛选通过的选题列表"
}
```

以及：

```json
{
  "name": "brand_guideline",
  "from": {
    "kind": "workflow_input",
    "name": "brand_guideline"
  },
  "shape": "file",
  "required": false,
  "summary": "品牌语气与禁用词约束文档"
}
```

#### 5.4 节点级 `outputs`

当前收敛版最小子字段为：

- `name`
- `shape`
- `summary`

例如：

```json
{
  "name": "article_draft",
  "shape": "file",
  "summary": "供后续审校节点处理的首版文案"
}
```

这里进一步确认：

- 节点声明出来的 `outputs`，默认就是该节点通过时应交付的合同产物。
- 因此，当前不建议在节点级 `outputs` 中再额外引入 `required` 字段。

#### 5.5 `executor`

当前收敛版最小子字段为：

- `skill`

例如：

```json
{
  "skill": "draft-wechat-article"
}
```

这里进一步确认：

- `executor` 在 spec 中的核心任务是说明“由哪个 Skill 执行该节点”。
- V1 当前不建议在 `executor` 内预埋过多配置。
- V1 中，`executor.skill` 先收敛为不透明字符串引用。
- Runtime 负责把这个字符串交给对应的 Skill 解析或分发机制处理，但 `workflow spec` 本身不展开 Skill 的来源协议、安装方式或版本解析规则。

#### 5.6 `validators`

当前建议：

- `validators` 使用数组承载。
- 每个 validator 至少包含：
  - `validator_id`
  - `skill`

例如：

```json
[
  {
    "validator_id": "content-review",
    "skill": "review-wechat-article"
  }
]
```

这里进一步确认：

- 引入 `validator_id`，是为了后续支撑多 Validator、Gate 聚合、Verdict 追踪与可读性展示。
- V1 中，`validators[].skill` 同样先收敛为不透明字符串引用，而不在 `workflow spec` 内重复设计 Skill 协议。

#### 5.7 `acceptance`

职责边界：

- `acceptance` 用于定义“什么叫这个节点完成且可被认为满足语义要求”。
- 它回答的是完成态与验收语义，而不是多个 validator 结果如何聚合。

当前收敛版最小子字段为：

- `done_means`
- `pass_condition`

例如：

```json
{
  "done_means": "产出一版结构完整、可供后续审校的公众号文案初稿",
  "pass_condition": [
    "文案结构完整",
    "逻辑自洽",
    "符合目标文风"
  ]
}
```

这里进一步确认：

- `done_means` 偏向帮助人类快速理解节点完成态。
- `pass_condition` 偏向表达规则化验收条件。
- 二者都属于节点合同本身，而不是运行态信息。

#### 5.8 `gate`

职责边界：

- `gate` 用于定义“validator 结果如何被聚合并决定是否放行到下一步”。
- 它回答的是通过策略，而不是节点产物本身什么样才算合格。

当前收敛版最小子字段为：

- `mode`

当前推荐的 V1 最小值为：

- `all_validators_pass`

例如：

```json
{
  "mode": "all_validators_pass"
}
```

这里进一步确认：

- V1 当前不建议提前引入复杂评分或加权聚合。
- 如后续确有需要，再演进更多 gate 模式。
- 可将二者理解为：`acceptance` 负责定义“什么是完成”，`gate` 负责定义“如何判定通过”。

#### 5.9 `handoff`

当前收敛版最小子字段为：

- `outputs`

例如：

```json
{
  "outputs": ["article_draft", "draft_meta"]
}
```

这里进一步确认：

- `outputs` 表示该节点承诺交付哪些产物。
- `handoff.outputs` 表示其中哪些产物作为下游正式接口参与流转。
- 在 V1 中，两者可能高度重合，这是可以接受的。

### 6. `defaults`（可选）

职责：

- 承载工作流级默认配置。
- 用于未来支持默认 gate、默认超时、默认返工上限等工作流级约束。

当前判断：

- 可选。
- V1 应保持克制，不应预埋过多内容。

### 7. `extensions`（可选）

职责：

- 作为未来扩展入口。
- 用于在不破坏顶层主结构的前提下承载额外能力。

当前判断：

- 可选。
- 应被视为扩展口，而不是杂项收纳盒。

当前补充一条最小使用约束：

- `extensions` 中的每个扩展项都应具备稳定命名空间，并应显式声明自身版本。
- 更推荐的形态是“具名扩展对象列表”或“按命名空间分组的结构化对象”，而不是无说明的散乱字段。
- V1 只定义这是扩展口，不要求 Runtime 原生理解其中内容；未知扩展默认应被忽略，而不是导致主协议失效。

---

## 七、当前推荐的最小骨架（已确认）

以下结构仅用于统一理解，不代表子字段已经全部最终定稿：

```json
{
  "schema_version": "pipeliner.workflow/v1alpha1",
  "metadata": {
    "workflow_id": "wechat-article-pipeline",
    "title": "公众号文案生产流程",
    "purpose": "从选题输入到审校通过，产出可发布的公众号文案",
    "version": "0.1.0",
    "tags": ["content", "wechat"]
  },
  "inputs": [
    {
      "name": "approved_topics",
      "shape": "json",
      "required": true,
      "summary": "已确认可写的选题列表"
    },
    {
      "name": "brand_guideline",
      "shape": "file",
      "required": false,
      "summary": "品牌语气、禁用词与文风约束文档"
    }
  ],
  "outputs": [
    {
      "name": "final_article",
      "from": {
        "node_id": "final_review",
        "output": "approved_article"
      },
      "shape": "file",
      "required": true,
      "summary": "最终通过验收、可对外发布的公众号文案"
    }
  ],
  "nodes": [
    {
      "node_id": "draft_article",
      "title": "生成初稿",
      "purpose": "根据筛选后的选题和品牌约束，生成公众号文案初稿",
      "archetype": "draft-content",
      "depends_on": ["select_topics"],
      "inputs": [
        {
          "name": "approved_topics",
          "from": {
            "kind": "node_output",
            "node_id": "select_topics",
            "output": "approved_topics"
          },
          "shape": "json",
          "required": true,
          "summary": "上游筛选通过的选题列表"
        },
        {
          "name": "brand_guideline",
          "from": {
            "kind": "workflow_input",
            "name": "brand_guideline"
          },
          "shape": "file",
          "required": false,
          "summary": "品牌语气、禁用词与文风约束文档"
        }
      ],
      "outputs": [
        {
          "name": "article_draft",
          "shape": "file",
          "summary": "供后续审校节点处理的首版文案"
        },
        {
          "name": "draft_meta",
          "shape": "json",
          "summary": "文案结构与统计摘要"
        }
      ],
      "executor": {
        "skill": "draft-wechat-article"
      },
      "validators": [
        {
          "validator_id": "content-review",
          "skill": "review-wechat-article"
        }
      ],
      "acceptance": {
        "done_means": "产出一版结构完整、可供后续审校的公众号文案初稿",
        "pass_condition": [
          "文案结构完整",
          "逻辑自洽",
          "符合目标文风"
        ]
      },
      "gate": {
        "mode": "all_validators_pass"
      },
      "handoff": {
        "outputs": ["article_draft", "draft_meta"]
      }
    }
  ],
  "defaults": {},
  "extensions": {}
}
```

这个骨架体现的关键不是字段名是否已经最终拍板，而是以下关系：

- 顶层先标识 schema 版本。
- 先定义 workflow 自身身份。
- 再定义 workflow 对外输入输出合同。
- 最后以 `nodes` 承载内部合同网络。
- 运行态信息不应混入其中。

---

## 八、当前明确不属于 Workflow Spec 的内容（已确认）

为了避免 `workflow spec` 膨胀，当前明确以下内容不应被设计进其顶层结构：

- Workflow Run 的实时状态
- 节点当前执行状态
- 回调历史
- Validator verdict 历史
- 返工轮次结果
- artifact manifest 本体
- artifact payload 本体
- UI 排版、图渲染和展示配置
- Skill 的内部能力声明与资源结构

这些对象都与工作流相关，但不属于工作流定义本身。

---

## 九、协议演进与兼容性约定（已确认）

当前补充以下跨版本规则，供 `workflow spec` 使用：

- `schema_version` 的主版本升级表示不兼容变更，需要显式迁移。
- `schema_version` 的次版本升级表示向后兼容的增量扩展，例如新增可选字段。
- 补丁级修订用于文档澄清或不改变协议含义的修正，不应要求调用方迁移。
- Runtime 在 V1 中至少应拒绝自己无法识别主版本的 spec，而不是静默猜测。

---

## 十、待继续讨论的内容

在顶层结构方向已经确认，且 `metadata / inputs / outputs / nodes` 已经收敛出当前薄版草案的前提下，后续应重点讨论以下内容：

### 1. `defaults` 的边界

例如：

- 哪些内容适合做成 workflow 级默认值。
- 哪些内容应明确留在节点级，不应上提到顶层。

### 2. `extensions` 的边界

例如：

- 哪些未来能力适合进入 `extensions`。
- 如何避免把 `extensions` 用成杂项收纳盒。

### 3. `nodes` 的进一步细化问题

例如：

- `depends_on` 与 `inputs.from` 的一致性应由何种 lint 规则约束。
- `gate.mode` 在 V1 之后是否需要扩展更多模式。
- `handoff` 在未来是否需要支持比 `outputs` 列表更丰富的交接视图。

---

## 十一、当前结论

截至目前，`workflow spec` 可以被概括为：

> 一份用于定义 Pipeliner 工作流的机器真源。
>
> 它描述 workflow 的身份、对外输入输出合同，以及内部节点合同网络。
>
> 它服务于 Authoring、Lint、Runtime 快照和视图派生，但不承载运行态结果与 UI 杂项细节。

更简洁地说：

```text
workflow spec = canonical workflow definition
```

这就是当前阶段对 `workflow spec` 的核心设计结论。
