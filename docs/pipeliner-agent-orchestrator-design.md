# Pipeliner：Skill 驱动的 Agent 任务编排器设计纪要

## 文档目的

本文档用于沉淀当前已讨论并基本达成一致的设计结论，避免后续在产品定义、节点抽象和 Skill 边界上反复摇摆。

本文档只记录两类内容：

- 已确定设计：当前已经明确、可作为后续设计基础的部分。
- 待确认事项：已经讨论过，但还没有最终拍板的部分。

---

## 一、项目定位（已确定）

Pipeliner 的目标不是做一个传统的脚本工作流平台，也不是做一个简单的 LLM Prompt Chain，而是做一个：

> 以 Skill 为执行单元、以产物为边界、以验收门为放行条件的 Agent 任务编排器。

更具体地说：

- 工作流中的每个节点，不是脚本任务，也不是一次性大模型调用。
- 每个节点本质上都是一个发给 Agent 的“工作单”。
- 节点必须有明确输入、明确产出、明确验收标准。
- 后续节点是否启动，不取决于“前置任务是否运行结束”，而取决于“前置节点产物是否通过验收”。

这也是 Pipeliner 与常见工作流系统的核心区别。

---

## 二、与常见工作流系统的区别（已确定）

从编排对象上看，Pipeliner 与常见系统并不相同：

- `Airflow / Temporal` 更偏向编排确定性代码任务。
- `n8n / Zapier` 更偏向编排 API、工具调用和集成流程。
- `LangGraph / CrewAI` 更偏向编排推理步骤、Agent 对话或多 Agent 协作。
- `Pipeliner` 编排的是“带交付物和验收门的 Agent 工作单”。

因此，Pipeliner 的核心不是控制 Agent 的中间过程，而是控制：

- 节点需要交付什么。
- 如何验证这些交付物是否达标。
- 什么时候允许下游继续执行。

一句话总结：

> Pipeliner 不强约束 Agent 如何工作，而强约束 Agent 何时算完成。

---

## 三、核心建模原则（已确定）

### 1. Workflow 是“任务合同”的依赖图

工作流不是一串脚本调用，而是一组节点合同的依赖关系：

```text
Workflow = 一组节点合同的依赖图
```

每条边传递的主语，也不应该是松散的自然语言上下文，而应该优先是：

- 已验收产物
- 产物引用
- 结构化交接信息

自然语言上下文可以存在，但应处于辅助地位。

### 2. Node 是“交付合同”，不是“执行步骤”

每个节点不是“做一件事”这么简单，而是一个完整的交付单元。当前已确认的节点组成如下：

```text
Node
├─ Input Contract
├─ Executor Skill
├─ Output Contract
├─ Validator Skill(s)
├─ Gate Policy
└─ Handoff
```

含义如下：

- `Input Contract`：节点可以读取哪些输入。
- `Executor Skill`：负责执行任务并产生产物的 Skill。
- `Output Contract`：节点必须交付哪些结果。
- `Validator Skill(s)`：负责检验结果是否符合要求的 Skill。
- `Gate Policy`：定义什么条件下算“通过”，允许下游继续。
- `Handoff`：定义哪些已验收结果会传给后续节点。

### 3. 编排器关注“收口”，不规定过程细节

Pipeliner 的关键设计立场是：

- 不强行规定 Executor Agent 的内部执行过程。
- 不要求节点必须通过单次结构化输出完成。
- 允许 Agent 使用自己的方式完成任务。
- 只在节点收口处定义清晰的验收边界。

这意味着系统重点管理的是：

- 委托内容
- 输出要求
- 验收标准
- 是否放行

而不是把 Agent 的中间步骤硬编码成流程节点。

---

## 四、Skill 驱动模型（已确定）

### 1. 每个节点的 Executor 和 Validator 都由 Skill 驱动

这是当前设计中非常关键的一点。

每个节点上的两个核心角色：

- 执行者（Executor）
- 验收者（Validator）

都应该由各自独立的 Skill 驱动，而不是依赖一套统一的通用模板。

也就是说：

- 不同节点可以绑定不同的 Executor Skill。
- 不同节点也可以绑定不同的 Validator Skill。
- 节点之间的差异，本质上来自 Skill 中定义的任务说明、校验标准和辅助脚本。

### 2. Skill 不只是提示词，还包括配套资源

结合当前已有 Skill 生态，节点 Skill 应至少允许包含以下内容：

```text
skill/
├─ SKILL.md
├─ scripts/
├─ references/
└─ assets/
```

其中：

- `SKILL.md`：该角色的任务说明、行为要求、交付要求。
- `scripts/`：辅助脚本，用于确定性处理或校验。
- `references/`：需要按需加载的参考材料。
- `assets/`：该 Skill 需要使用的模板或资源文件。

这里的重点是：

- Skill 既可以承载自然语言任务描述。
- 也可以承载脚本化、可执行、可重复使用的工具能力。

### 3. Validator 逻辑应由节点专属 Skill 决定

当前已明确：

- Validator 不应依赖单一统一的“判卷模板”。
- 不同节点的判定逻辑可以完全不同。
- 这种差异主要通过不同的 Validator Skill 来表达。

例如：

- 对于 JSON 产物节点，Validator Skill 可以包含 JSON 校验提示词和格式校验脚本。
- 对于开放式文案节点，Validator Skill 可以包含定性质量判断提示词，例如逻辑通顺、结构完整、风格符合预期等。

换句话说，Validator 的“脑子”应该跟着节点需求走，而不是被强行抽象成一个统一模板。

### 4. 节点级 Skill 之外，还存在全局工作流生成 Skill

除了节点上的 `Executor Skill` 和 `Validator Skill` 之外，系统还需要一个更上层的、面向工作流创作的全局 Skill。

这个全局 Skill 不服务某个具体节点，而是服务整个工作流的生成、修改和细化过程。

它的作用是指导 `Claude Code`：

- 如何理解用户想要的 Pipeline。
- 如何把模糊需求逐步拆成节点。
- 如何为节点补齐输入、输出、验收和依赖关系。
- 如何在多轮对话中持续微调工作流结构和节点细节。

换句话说，Skill 在 Pipeliner 中不只承担“节点执行”和“节点验收”的职责，也承担“工作流创作”的职责。

---

## 五、工作流生成方式（已确定）

Pipeliner 的工作流生成方式，不应主要依赖手写 DSL 或手工配置表单，而应以 `Claude Code` 驱动的对话式生成作为核心入口。

当前已明确的方向是：

- 在开发 Pipeliner 时，提供一个全局、通用的 Workflow Authoring Skill。
- 该 Skill 专门用于指导 `Claude Code` 如何生成和修改工作流。
- 用户通过与 `Claude Code` 的多轮对话，逐步把自己想要的 Pipeline 雕琢出来。
- 这种雕琢可以深入到每个节点、每条依赖边和每项验收细节。

这种方式的意义在于：

- 用户不必一开始就掌握完整的工作流配置语法。
- 工作流定义可以在对话中逐步成形，而不是一次性设计完毕。
- 节点级细节可以被反复调整，直到满足实际需求。

因此，Pipeliner 的工作流设计入口，本质上是：

```text
用户意图 → Claude Code + 全局 Authoring Skill → 逐步成形的 Workflow
```

### 1. 工作流应同时具有机器真源与人类可理解视图

当前进一步确认：

- 工作流不应只存在一种“原始机器表示”。
- 系统内部需要有一个机器可读、可校验、可执行的唯一真源。
- 同时也需要有一个面向人类阅读和理解的可视图层。

当前建议将工作流的表达分为三层：

- `Intent Brief`：用户意图、目标、约束、验收偏好等对话起点。
- `Workflow Spec`：机器可读、可执行、可验证的唯一真源。
- `Workflow View`：面向人类阅读的摘要、图示、节点卡片和结构说明。

这里的关键不是复制三份不同真相，而是：

- 让系统围绕 `Workflow Spec` 运作。
- 让用户主要通过 `Workflow View` 理解与修改工作流。
- 让 `Claude Code` 在 `Intent Brief` 与 `Workflow Spec` 之间承担生成、补齐和重构职责。

### 2. Claude Code 生成的应是固定结构的 Workflow Package

当前建议并纳入设计文档：

- `Claude Code` 不应只输出一段说明文字，或一份缺乏上下文的人机混合产物。
- 更合适的做法是生成一个固定结构的 `workflow package`。

当前建议的最小组成包括：

- `workflow.spec.json`：机器可读的 canonical workflow。
- `workflow.view.md`：面向人类阅读的工作流说明。
- `workflow.graph.*`：图结构表达，可采用 Mermaid、ASCII 或其他可渲染形式。
- `authoring.report.json`：可选的作者期校验报告，例如 schema/lint 结果。

这里需要强调：

- `workflow.spec.json` 是唯一真源。
- 其他文件是围绕它派生的可理解视图或校验报告。
- 文件名当前用于表达设计意图，后续仍可微调，但“固定 package 结构”的原则已经确认。

### 3. Node Card 应成为人类理解工作流的基本单位

当前确认：

- 用户理解工作流时，不应直接暴露在全部底层协议细节之中。
- 更自然的阅读单位应是节点卡片，而不是原始 callback payload、artifact manifest 或其他内部协议对象。
- 这里讨论的 `Node Card`，首先是设计态对象，而不是运行时状态对象。

也就是说：

- `Node Card` 主要用于表达节点合同在设计层的含义。
- 运行中的轮次状态、最新 verdict、回调日志等，如果后续需要展示，更适合作为独立的运行态面板或运行态卡片，而不应混进设计态 `Node Card`。

当前建议每个 `Node Card` 至少回答：

- 这个节点要做什么。
- 它读取哪些输入。
- 它交付哪些产物。
- 它由哪个 `Executor Skill` 执行。
- 它由哪个 `Validator Skill` 验收。
- 它在什么条件下算通过。
- 它未通过时会如何返工。
- 它最终向下游交接什么。

这意味着在工作流的人类视图层中，节点应优先被渲染为卡片，而不是一坨生硬的协议字段。

#### Node Card 的角色边界（已确定）

当前进一步确认，`Node Card` 的职责是：

- 作为节点合同的人类阅读单元。
- 作为对话式工作流修改的自然落点。
- 作为工作流评审与审查的基本单位。
- 作为默认入口，但不是唯一入口。

这意味着：

- 用户默认通过 `Node Card` 理解工作流。
- 高级用户应始终可以从卡片下钻到底层 `workflow spec`。
- `Node Card` 不应取代 canonical spec，也不应成为第二份真源。

#### Node Card 的当前最小字段集（已确定）

在当前设计下，建议 `Node Card` 采用固定字段集，而不是完全自由的自然语言描述。

推荐的最小字段包括：

- `node_id`
- `title`
- `purpose`
- `archetype`
- `depends_on`
- `inputs`
- `outputs`
- `executor_skill`
- `validator_skills`
- `done_means`
- `pass_condition`
- `on_revise`
- `handoff`

这里特别确认两点：

- `purpose` 用于解释该节点为什么存在。
- `done_means` 用于用人类可理解的话说明“这个节点什么时候算真的完成”。

其中：

- `pass_condition` 更偏向规则化验收条件。
- `done_means` 更偏向帮助人类快速理解节点完成态。

#### Node Card 的推荐结构分组（已确定）

为了兼顾可读性与稳定性，当前建议把 `Node Card` 按如下结构分组展示：

```text
Node Card
├─ Identity
│  ├─ node_id
│  ├─ title
│  ├─ archetype
│  └─ purpose
├─ Topology
│  ├─ depends_on
│  └─ downstream
├─ Input Contract
│  └─ inputs[]
├─ Output Contract
│  └─ outputs[]
├─ Roles
│  ├─ executor_skill
│  └─ validator_skills[]
├─ Acceptance
│  ├─ done_means
│  └─ pass_condition
└─ Flow
   ├─ on_revise
   └─ handoff
```

这里的重点不是字段名必须永远固定不变，而是：

- 卡片应优先表达节点合同。
- 卡片应有稳定的信息分组。
- 卡片应首先服务“快速理解”，而不是复刻全部底层协议细节。

#### Node Card 应提供默认视图与高级视图（已确定）

当前进一步确认：

- 为兼顾可读性与可编辑性，`Node Card` 应采用渐进暴露策略。
- 默认视图面向快速理解。
- 高级视图面向技术用户的深度查看与底层调整。

默认视图中，优先展示：

- `title`
- `purpose`
- `depends_on`
- `inputs`
- `outputs`
- `executor_skill`
- `validator_skills`
- `done_means`
- `handoff`

其中，`inputs/outputs` 当前建议采用摘要展示粒度，而不是直接展开到底层 artifact 或存储实现细节。

推荐的默认摘要字段为：

- 对 `inputs`
  - `name`
  - `from`
  - `shape`
  - `required`
  - `summary`
- 对 `outputs`
  - `name`
  - `shape`
  - `summary`
  - `accepted_as`
  - `handoff_to`

这里的设计目标是：

- 先让用户快速理解节点合同。
- 不让卡片默认膨胀成协议调试面板。
- 把更细的底层信息留给高级视图。

对于 `shape`，当前确认的设计立场是：

- 应先内置一组常用、足够稳定的基础类型，例如：
  - `text`
  - `json`
  - `file`
  - `directory`
  - `collection`
- 同时不应把 `shape` 设计成封闭枚举。
- 由于 Runtime 传递的是引用而不是文件本体，因此系统可以支持更多文件类型或更细粒度的资源形态。
- 关键不在于 Runtime 是否理解文件内容，而在于后续节点绑定的 Agent / Skill 是否具备处理该引用所指向交付物的能力。
- 不同文件类型的处理能力，应主要通过 Skill 扩展，而不是强行固化在 Runtime 内部。
- Skill 本身的内部组织与规范，应遵循既有的 Skill 设计约定；Pipeliner 只负责引用 Skill、在节点上绑定 Skill，而不重新定义 Skill 的内部能力声明机制。

这意味着：

- Runtime 主要关心引用是否可追踪、可定位、可交接。
- Pipeliner 主要关心节点是否正确绑定了合适的 Skill。
- Skill 决定某类输入输出是否“可被消费”和“可被处理”。

高级视图中，可进一步展示：

- 原始 `skill ref`
- 更细的 `input/output contract`
- `gate policy` 细节
- 与底层 `workflow spec` 的映射
- 校验与 lint 结果

这里需要强调：

- “更容易理解”不应通过彻底隐藏底层结构来达成。
- 技术用户应始终保留查看和修改底层细节的能力。

#### Node Card 不应混入的内容（已确定）

为了避免卡片膨胀，当前确认以下内容不应默认混入设计态 `Node Card`：

- 当前运行状态
- 最新 round 编号
- 最近一次 validator verdict 详情
- callback payload 原文
- 执行日志
- workspace 真实路径
- artifact manifest 的完整底层字段

这些信息若需要展示，应在运行态视图、调试视图或底层详情面板中承载，而不是塞进设计态节点卡片。

#### Node Card 与 Workflow Spec 的关系（已确定）

当前进一步明确：

- `workflow.spec.json` 仍然是唯一真源。
- `Node Card` 更适合作为从 `workflow spec` 派生出来的人类视图和编辑载体。
- V1 不建议把 `Node Card` 再做成另一份独立真源文件，以免引入双向同步与双真源问题。

一句话概括：

> Node Card 是受约束的人类视图模型，而不是另一份 canonical spec。

### 4. Authoring 应优先复用节点原型，而不是完全自由生成

当前进一步确认：

- 为了降低工作流创建成本，也为了约束 `Claude Code` 的输出漂移，应为常见节点类型预置可复用的节点原型（archetype）。
- 工作流创作时，应优先采用“选择原型 + 补齐细节”的方式，而不是让模型每次从零发明节点结构。

例如可预置的原型方向包括：

- `generate-json`
- `structured-extract`
- `draft-content`
- `review-content`
- `batch-generate`
- `batch-review`
- `package-export`
- `research-summarize`

这里的目标不是把系统做成僵硬模板库，而是通过原型减少无谓自由度，提高生成结果的稳定性与可维护性。

### 5. Workflow Authoring 本身也应有 Validator / Linter

当前确认：

- 工作流创作本身，也应遵循“先生成，再校验，不通过则返工”的总体哲学。
- 因此，`Claude Code` 生成的 workflow package 不应直接视为最终结果，而应进入一层作者期校验。

推荐的流程为：

```text
用户意图
  → Claude Code + Authoring Skill 生成候选 workflow package
  → Authoring Validator / Linter 校验
  → pass：成为正式 workflow
  → revise：反馈给 Claude Code 继续修正
```

当前建议 Authoring Validator / Linter 至少覆盖以下方向：

- `schema` 完整性
- 图结构合法性
- 节点合同完整性
- Skill 引用合法性
- Artifact 输入输出闭合性
- 命名规范
- 可理解性检查

这里的“可理解性检查”也应被视为正式约束的一部分，而不只是附加建议。

### 6. 设计目标是降低理解成本，而不是隐藏底层能力

当前进一步明确：

- Pipeliner 的目标用户，应默认是具有一定技术背景的使用者，而不是完全零门槛的普通用户。
- 因此，系统需要降低理解成本，但不应为了追求表面易用而过度隐藏底层细节。
- 对用户友好，并不意味着取消对底层协议、节点合同、Artifact 引用、Lint 结果的访问和修改能力。

当前更合适的设计立场是：

- 默认提供更容易理解的视图，例如节点卡片、图结构和摘要说明。
- 同时保留用户直接查看和修改底层 `workflow spec`、节点细节、Skill 绑定和验收约束的能力。
- 采用“渐进暴露”而不是“彻底封装”的方式处理复杂度。

一句话概括：

> 对用户提供更好的抽象，但不以牺牲可控性和可编辑性为代价。

---

## 六、产物优先，而不是上下文优先（已确定）

Pipeliner 的边界对象应优先是“产物”，而不是“上下文”。

这是当前已经比较明确的一条原则：

- 下游节点应该消费上游节点的已验收产物。
- 不应默认依赖上游完整对话上下文。
- 自然语言说明可以作为辅助交接信息，但不应该成为主依赖。

这样做的好处是：

- 节点边界更清晰。
- 验收对象更具体。
- 下游依赖更稳定。
- 系统不会退化成普通的 Prompt Chaining。

因此，Pipeliner 的编排对象更接近：

```text
Artifact Flow > Context Flow
```

---

## 七、节点输出应可被验收和传递（已确定）

每个节点都必须有明确输出，这些输出不应只是“任务完成”这种模糊状态，而应是可交付、可判定、可供下游消费的产物。

这意味着节点输出需要满足以下特性：

- 可定位：知道输出在哪里。
- 可检查：知道输出是否符合要求。
- 可传递：知道哪些内容会进入下游。
- 可复用：下游节点不需要重新猜测上游结论。

对某些节点来说，输出可以是：

- JSON 字符串
- 文件
- 文档
- 摘要
- 结构化中间结果

对另一些更开放的节点来说，输出也可以是：

- 文案稿件
- 分析结论
- 研究摘要
- 方案说明

只要它们满足“可验收、可交接”的要求，就可以成为节点产物。

---

## 八、交付物流转与运行工作目录（已确定）

Pipeliner 需要同时面对小文本交付物与大文件、多文件、目录型交付物。

当前进一步确认，系统在运行态上必须区分两层：

- 控制面（Control Plane）：负责流转 `artifact reference`、回调消息、验收结论、返工单和状态记录。
- 数据面（Data Plane）：负责承载真正的文件、目录、文件集合和其他较大交付物实体。

因此，对于较大文件或一批文件，当前明确的设计立场是：

- 在 Pipeline 中流动的，默认不应是大文件本体，而应是 `artifact reference + artifact manifest`。
- `Runtime` 负责记录和转发交付物引用，而不负责在协议层搬运大文件字节流。
- 节点之间不应通过猜测上游裸文件路径来耦合，而应通过正式的 `artifact reference` 和 `handoff` 机制获取交付物。

一句话概括：

> Pipeline 传递的是交付物身份，而不是交付物实体。

### 1. 每个 Workflow Run 都应有独立的工作根目录

当前确认：

- 每一次工作流运行实例，都应拥有自己的独立工作根目录。
- 该目录用于沉淀本次运行的过程文件、正式交付物、节点返工轮次以及事件轨迹。
- 这样既有利于追踪每次运行的完整过程，也为大文件、多文件交付物提供了稳定落点。

推荐的根目录形态为：

```text
runs/<pipeline_slug>/<run_id>/
```

其中：

- `pipeline_slug` 用于人类可读地标识工作流。
- `run_id` 用于系统唯一识别本次运行实例。
- 时间信息可以体现在 `run_id` 或元数据中，但不应只依赖纯时间戳充当唯一标识。

### 2. Run Root 中应显式区分元数据、节点轮次与正式交付物

当前建议并纳入设计文档的目录结构如下：

```text
runs/
└─ <pipeline_slug>/
   └─ <run_id>/
      ├─ run.json
      ├─ workflow.snapshot.json
      ├─ events.ndjson
      ├─ artifacts/
      │  └─ <artifact_id>@v1/
      │     ├─ manifest.json
      │     └─ payload/
      └─ nodes/
         └─ <node_id>/
            ├─ node.json
            ├─ rounds/
            │  └─ 001/
            │     ├─ executor/
            │     │  ├─ input_refs.json
            │     │  ├─ workspace/
            │     │  ├─ submission.json
            │     │  └─ logs/
            │     ├─ validators/
            │     │  └─ <validator_id>/
            │     │     ├─ input_refs.json
            │     │     ├─ workspace/
            │     │     ├─ verdict.json
            │     │     └─ logs/
            │     └─ gate.json
            └─ accepted.json
```

这里的含义是：

- `run.json`：记录本次运行的基础元数据。
- `workflow.snapshot.json`：记录本次运行锁定的工作流快照。
- `events.ndjson`：记录运行中的关键事件，便于追踪与回放。
- `artifacts/`：存放本次运行中已经正式发布的交付物版本。
- `nodes/<node_id>/rounds/`：记录节点的多轮执行、验收与返工过程。
- `accepted.json`：记录该节点最终放行给下游的正式交付物引用。

### 3. 节点目录必须区分工作区与正式提交物

当前进一步明确：

- `workspace/` 是 Agent 可自由读写的工作区。
- `submission.json` 以及其关联的正式交付物，是本轮提交给系统验收的收口结果。
- `workspace/` 中的内容可以继续变化，但一旦交付物被正式发布，就应作为验收对象和下游依赖对象固定下来。

这意味着系统中至少需要区分两个概念：

- `workspace path`：Agent 在执行中使用的临时路径。
- `artifact reference`：节点正式提交、系统正式记录、下游正式消费的交付物引用。

两者不能混用。

### 4. 节点返工应按轮次建模，而不是覆盖旧状态

由于一个节点可能经历多轮：

```text
Executor 提交
  → Validator 验收
  → revise
  → Executor 返工后再次提交
  → Validator 再次验收
```

因此当前确认：

- 节点目录不应只保存“一次最新状态”。
- 节点应显式建模为多个 `round`。
- 每一轮都应能够回看：输入是什么、提交了什么、Validator 如何判定、为什么返工。

这既是返工闭环的基础，也是系统后续可观察性、可回放性的基础。

### 5. 正式发布的交付物应当不可变，返工产生新版本

当前确认：

- 一旦交付物被发布到 `artifacts/` 并获得正式引用，就应视为不可变。
- 后续返工不应就地修改既有版本，而应产生新的版本。
- `Validator`、`Runtime` 和下游节点都应围绕明确版本进行协作，而不是围绕一个会被偷偷改写的路径协作。

例如：

```text
artifact_x@v1
artifact_x@v2
artifact_x@v3
```

而不是持续修改同一个 `artifact_x@v1`。

### 6. V1 先以本地文件系统作为第一个存储后端

当前建议并纳入设计文档：

- V1 不急于引入对象存储、远程共享卷或复杂的外部存储抽象。
- V1 先以本地文件系统作为第一个 `storage backend`。
- 先把 `run root + artifact manifest + artifact reference` 这一套工作流运行骨架跑通。

后续如果需要扩展到：

- 对象存储
- 外部文件系统
- 外部系统对象引用

也应尽量通过扩展 `artifact manifest` 的存储描述来实现，而不是推翻前述协议层边界。

### 7. Handoff 传递的应是正式引用，而不是裸路径

当前进一步明确：

- 上游节点不应要求下游直接读取类似 `../node-a/output.md` 这样的裸路径。
- `Handoff` 传给下游的应是正式的 `artifact reference`，必要时附带视图、筛选或物化提示。
- 下游节点应通过引用解析到实际路径、目录或外部对象位置，而不是自行猜测上游目录结构。

这样做的目的在于：

- 保持协议层稳定。
- 避免节点间通过临时路径硬耦合。
- 为后续切换存储后端、支持多文件交付和多轮返工保留空间。

### 8. Artifact Manifest 应保持薄核心，而不是无限膨胀

当前进一步确认：

- `artifact manifest` 是交付物的正式登记信息，而不是一个包打天下的杂项容器。
- 它的职责应收敛为：标识交付物、锚定版本、说明来源、给出存储位置、提供完整性校验信息。
- 它不应天然承载验收结论、返工反馈、执行日志、完整业务解释、下游消费规则等其他对象的职责。

换句话说：

```text
manifest = 登记表
而不是
manifest = 档案袋
```

因此，当前建议把相关对象明确拆开：

- `artifact ref`：工作流中传递的轻量引用。
- `artifact manifest`：交付物的薄核心登记信息。
- `artifact index`：当交付物是一批文件或大型集合时，用于展开明细的可选索引。
- `verdict / rework brief`：由 Validator 产出的验收结论与返工单。
- `handoff`：面向下游节点的消费说明。

### 9. Artifact Manifest 的当前收敛版最小字段

在“薄核心”原则下，当前建议 `artifact manifest` 至少回答以下问题：

- 它是谁。
- 它是哪一版。
- 它从哪来。
- 它存在哪。
- 如何确认它没有被偷偷改动。

据此，当前建议的最小字段分组为：

- 身份层
  - `artifact_id`
  - `version`
  - `kind`
- 来源层
  - `produced_by.run_id`
  - `produced_by.node_id`
  - `produced_by.round_no`
- 存储层
  - `storage.backend`
  - `storage.uri`
- 完整性层
  - `integrity.digest`
- 时间层
  - `created_at`

在此之上，可以保留一层非必填的轻量描述字段，用于改善消费体验，但不应挤进核心必填集合：

- `media_type`
- `entrypoint`
- `index_file`
- `item_count`

当前也进一步明确，以下内容不应默认进入 `artifact manifest` 的核心层：

- `verdict`
- `rework_brief`
- `handoff` 规则
- 完整文件清单
- 执行日志
- 业务说明长文本

对于大批量文件或目录型交付物，更推荐的做法是：

- 让 `manifest` 保持轻量。
- 让详细展开信息进入可选的 `index` 文件。
- 由下游节点通过 `manifest` 中的索引入口按需读取，而不是把所有明细硬塞进 `manifest` 本体。

---

## 九、典型节点示例（已确定）

### 示例 1：JSON 产物节点

目标：根据输入，输出满足要求的 JSON 字符串。

该节点可以设计为：

- `Executor Skill`
  - 在 `SKILL.md` 中说明输入语义、目标 JSON 的含义、字段要求和输出方式。
- `Validator Skill`
  - 在 `SKILL.md` 中说明如何从验收视角检查输出。
  - 在 `scripts/` 中提供 JSON 格式或 Schema 校验脚本。
  - 在提示词中明确要求优先使用脚本进行验证。

这样，节点是否通过，不是看模型“声称自己完成了”，而是看产物是否通过明确校验。

### 示例 2：开放式文案节点

目标：生成一篇微信公众号文案。

该节点可以设计为：

- `Executor Skill`
  - 在 `SKILL.md` 中描述目标读者、语气、结构、篇幅和写作目标。
- `Validator Skill`
  - 在 `SKILL.md` 中定义定性判断标准，例如：
    - 逻辑是否通顺
    - 结构是否完整
    - 论述是否自洽
    - 文风是否符合要求

这里的关键不是把质量检查简化成某个通用脚本，而是允许该节点按自身目标配置合适的定性验收方式。

---

## 十、运行反馈与 API 汇报机制（已确定）

Pipeliner 不仅要负责生成和执行工作流，还必须解决一个关键问题：

- 节点中的 Agent 完成工作后，如何把结果可靠地反馈回工作流进程。

当前已明确的方向是使用 API 回调机制。

具体来说：

- 工作流运行进程需要监听一个专用端点。
- 每个节点中的 `Executor` 或 `Validator` 在完成工作后，都必须调用该端点进行汇报。
- 汇报内容应包括执行结果及其产出。
- 产出形式可以是字符串、文件、状态码或其他可被系统消费的结果。

Pipeline 运行进程在收到汇报后，负责：

- 识别当前是哪一个工作流、哪一个节点、哪一个角色、哪一轮执行的汇报。
- 接收并记录对应产物、状态结果和反馈信息。
- 按预先定义好的协议推进消息流转。
- 维护节点在执行、验收、返工、通过等阶段中的状态。

这里需要特别强调：

- `Runtime` 不负责判断内容质量。
- `Runtime` 不充当语义层裁判。
- `Validator` 才是节点产物是否合格的判断者。

因此，`Runtime` 的职责更准确地说是：

- 消息接收者
- 状态记录者
- 协议转发者
- 流转推进者

它是一个“传话者”，而不是“裁判者”。

这意味着，节点与编排器之间的关系不是“执行结束即默认完成”，而是：

```text
Executor 完成工作
  → 调用工作流端点汇报结果与产物
  → Runtime 接收并转交给 Validator
  → Validator 给出 pass / revise / blocked 结论，以及对应反馈
  → Runtime 将 revise 反馈转回 Executor，将 blocked 标记为待介入状态，或将 pass 结果放行给下游
```

在这个模型里：

- `Executor` 负责完成任务并提交产物。
- `Validator` 负责判断产物是否通过标准，并在不通过时产出可执行的返工反馈。
- `Runtime` 只负责把消息送到正确的位置，并推动预先定义好的流程继续前进。

这个回调机制是整个系统可运行、可判定、可往返返工、可自动流转的关键一环。

### 1. Validator 的失败反馈不应只是评论，而应是一张返工单

当前进一步确认：

- `Validator` 在未通过时，不应只返回一段松散的自然语言评论。
- 更合适的抽象是返回一张可执行的“返工单”。
- 这张返工单既要能被 `Runtime` 记录和转发，也要能让 `Executor` 在尽量少追问的情况下开始返工。

这里延续前面的总体设计立场：

- 协议层保持尽量薄。
- 节点级 Skill 保持足够厚。

也就是说：

- 统一的是最小回传外壳。
- 不统一的是各个节点内部的判定思路、提示词、脚本和质量标准。

### 2. Validator 输出应分为两层：Verdict Envelope 与 Rework Brief

当前确认，`Validator` 的输出可抽象为两层：

```text
Validator Output
├─ Verdict Envelope
└─ Rework Brief
```

其职责分工如下：

- `Verdict Envelope`：给 `Runtime` 看，用于流转推进、状态记录和追踪。
- `Rework Brief`：给 `Executor` 看，用于明确指出需要如何返工。

在概念上，`Verdict Envelope` 至少应包含：

- `status`：本次语义结论。
- `target_artifact`：本次验收针对的是哪一个产物版本。
- `summary`：对本次结论的简短总结。
- `validator_identity`：由哪个 Validator Skill、哪一轮运行给出了该结论。

在概念上，`Rework Brief` 至少应包含：

- `must_fix[]`：必须修正的问题列表。
- `preserve[]`：明确哪些内容不应被返工破坏。
- `resubmit_instruction`：返工后应按什么形式重新提交。
- `evidence[]`：可选的判定依据，例如脚本输出、错误片段、规则命中情况。

这里需要说明：

- 上述字段名称当前用于表达最小设计意图。
- 后续在协议层上如何命名、如何序列化，仍属于待进一步收敛的问题。

### 3. 语义 Verdict 状态先收敛为三类

当前建议并纳入设计文档的最小状态集为：

- `pass`：验收通过，可以放行下游。
- `revise`：验收未通过，但问题仍处于可返工范围，应将返工单送回 `Executor`。
- `blocked`：当前不适合继续自动返工，通常意味着缺少前提、约束冲突或需要人工介入。

之所以不直接使用单纯的 `fail`，是因为：

- `fail` 无法区分“应该继续返工”与“当前不应继续返工”。
- 对运行时流转而言，`revise` 和 `blocked` 的后续动作不同。

### 4. 运行状态与语义结论应当分层

当前进一步明确：

- `Validator` 给出的 `pass / revise / blocked`，属于语义层验收结论。
- 超时、脚本报错、Agent 崩溃、回调失败等，属于运行层状态。

这两层信息不应混在同一个字段里。

也就是说：

- “Validator 认为内容不合格”
- 和 “Validator 这次根本没成功执行完”

是两类完全不同的问题。

前者决定业务语义上的放行与返工，后者决定运行时的重试、报错和人工介入。

### 5. 验收反馈必须绑定到明确的产物版本

当前确认：

- `Validator` 的结论必须明确指向某个具体产物版本。
- 否则系统很容易在多轮返工中失去“这次到底在验哪一版”的上下文锚点。

这意味着系统后续在协议层至少要能够表达：

- 本次提交的是哪一版产物。
- 本次验收针对的是哪一版产物。
- 下游放行拿到的是哪一版产物。

这一点是保证返工闭环、状态可追踪、结果可回放的基础。

### 6. 一个最小示意结构

以下结构只是帮助统一理解，不代表字段名已经最终拍板：

```json
{
  "verdict": {
    "status": "revise",
    "target_artifact": "artifact_x:v3",
    "summary": "JSON 结构基本正确，但缺少必填字段且一个字段类型错误",
    "validator_identity": "validator/json-check@run-7"
  },
  "rework_brief": {
    "must_fix": [
      {
        "target": "$.items[2].title",
        "problem": "缺少必填字段",
        "expected": "必须是非空字符串"
      },
      {
        "target": "$.total",
        "problem": "类型错误",
        "expected": "必须为整数"
      }
    ],
    "preserve": [
      "保持现有字段命名不变",
      "不要修改已经通过校验的 items[0..1]"
    ],
    "resubmit_instruction": "重新提交完整 JSON 字符串，不要附加解释文本",
    "evidence": [
      "validate_json.py 返回 exit code 1"
    ]
  }
}
```

这个结构体现的关键不是字段名，而是以下关系：

- 要有结论。
- 要有返工单。
- 要能锚定目标产物版本。
- 要让 `Executor` 能直接据此返工。

---

## 十一、产品价值判断（已确定）

当前讨论已经比较明确地指向一个现实价值：

- 某些模型或服务的价值入口，不一定是标准 API。
- 一些包月型服务可以通过 `Claude Code`、`OpenCode` 等 Agent 入口使用。
- 这种使用方式不适合直接当作常规 API 编排。
- 但可以通过“节点委托 + 技能驱动 + 验收放行”的方式，被系统化地组织起来。

因此，Pipeliner 的一个重要价值，不只是“让 Agent 跑任务”，而是：

- 将可对话、可代理、可持续执行的 Agent 通道，转化为可批量编排的生产能力。
- 通过节点级验收机制，提升包月型 Agent 通道的可控性和可复用性。
- 最大化利用包月服务在复杂任务处理上的实际产能。

---

## 十二、当前暂不视为已拍板的事项（待确认）

以下内容已经讨论过，但目前还不应当当作最终确定设计：

### 1. Skill 是否需要额外的机器可读 Manifest

目前已经明确 `SKILL.md + scripts/ + references/` 是可行方向。

但是否还需要额外引入类似 `skill.manifest.yaml` 的机器可读层，用于：

- 参数声明
- 输入输出声明
- 依赖说明
- 运行约束
- UI 展示

这个问题尚未最终拍板。

### 2. Gate Policy 的具体表达方式

目前已经明确节点必须有“通过后才放行”的机制。

但以下问题还没有最终定稿：

- 一个节点是否允许多个 Validator Skill。
- 多个 Validator 时采用“全部通过”还是“部分通过”。
- 在已经确定的最小 Verdict / Rework Brief 模型之上，是否扩展分数制、标签化理由、风险等级等更丰富的 verdict 结构。
- 当交付物是一批文件或目录时，验收单位应采用整批、分区还是单 item。

### 3. 运行时护栏如何建模

我们已经触及但尚未定稿的问题包括：

- 超时如何处理。
- 返工次数如何限制。
- Skill 版本如何固定。
- 节点失败后的人工介入策略。

这些都属于运行时设计问题，后续需要单独展开。

### 4. 核心协议的当前收敛状态

截至目前，三份核心协议与一份运行时护栏设计已经有了独立文档，并完成 V1 薄版收敛：

- `workflow spec`：见 `docs/workflow-spec-design.md`
- `node callback payload`：见 `docs/node-callback-payload-design.md`
- `artifact manifest`：见 `docs/artifact-manifest-design.md`
- `runtime guards`：见 `docs/runtime-guards-design.md`

从进入实施的角度看，当前主要阻塞设计已经基本收敛；后续剩余的问题更多属于实现细化与演进设计，而不再是 V1 的前置阻塞项。

### 6. 技术栈选择与实现节奏（已确认）

当前已经确认一份独立技术栈文档，用于说明为什么 V1 先采用 Python 优先的实现路线，以及为什么当前阶段只做最简单可用 GUI：

- `docs/tech-stack-decision.md`

其核心结论是：

- V1 先用 `Python` 完成后端核心。
- 先做最简单可用 GUI，不把复杂 Web 前端当成当前阻塞项。
- 等 Runtime、协议与 Artifact 闭环验证通过后，再用 Web 技术升级 UI/UX。

---

### 5. Workflow Package、Node Card 与 Authoring Lint 的具体格式

工作流创作的人类可理解性与 Authoring 约束方式已经确认方向，但以下具体格式仍待进一步收敛：

- `workflow package` 的最终目录结构和文件命名是否需要进一步标准化。
- `Node Card` 的排序方式和可视化渲染形式应如何确定。
- `shape` 字段的扩展机制与命名约定应如何进一步标准化，同时避免越界到 Skill 内部规范。
- `Authoring Validator / Linter` 的规则清单、严重级别和返工反馈格式应如何设计。

这些问题不会改变当前已确认的总体方向，但会影响后续协议与工具层的落地细节。

---

## 十三、当前结论

截至目前，可以把 Pipeliner 概括为：

> 一个面向 Agent 工作单的任务编排器。
>
> 它以 Skill 作为执行与验收的承载体，以产物作为节点之间的边界，以验收门作为工作流继续执行的前提条件。
>
> 它还通过全局 Authoring Skill 支持用户与 `Claude Code` 对话式生成工作流，并以 `workflow spec` 作为机器真源、以节点卡片和图视图作为人类理解入口，再通过 API 回调机制接收节点结果、驱动运行时流转。
>
> 在运行态上，它为每个 Workflow Run 提供独立工作根目录，以正式发布的 Artifact 引用而不是裸路径或大文件本体来驱动节点间流转。
>
> 它追求降低理解成本，但不以隐藏底层细节为代价；对于有技术背景的用户，应始终保留查看和修改底层工作流结构的能力。

更简洁地说：

```text
Pipeliner = Skill-driven + Artifact-gated + Agent-oriented Orchestrator
```

这是当前讨论中最核心、最稳定的产品定义。
