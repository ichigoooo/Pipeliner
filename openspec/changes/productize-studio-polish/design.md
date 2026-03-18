## Context

Pipeliner 当前已经具备从 authoring、发布、启动 run、自动驱动、attention 介入到迭代的主要工作流，核心问题已经从“功能是否存在”转向“异常是否解释得清楚、操作是否顺手、文档是否可信”。最近的未收口改动也集中在同一个方向：Claude 连接诊断、慢启动告警、运行列表清理和设置页补充诊断信息。这说明系统的下一个瓶颈不是继续扩展功能面，而是把现有能力压实为可持续运维的产品体验。

另外，当前仓库里还存在一个已完成但未归档的 `delete-run-workspace` change，说明主规格与实现之间已经开始出现时间差。此次设计需要兼顾两个约束：一是不重写 runtime 协议和状态机，二是把用户能直接感知到的运行语义和运维信息统一起来。

## Goals / Non-Goals

**Goals:**
- 在 executor、validator、authoring 三类 Claude 调用之间复用一套环境采集、预检和错误分类逻辑。
- 把“首字节慢启动”定义为可见警告而不是终态失败，并确保真实超时的 stop reason 语义稳定。
- 让 Studio 在终端无输出时仍能解释“排队中 / 已启动未出字 / 慢启动 / 连接失败”的差异。
- 让运行列表更适合日常运维，支持按优先级分组查看并批量清理非运行中历史项。
- 更新 README 与开发计划，使文档重新反映当前产品基线与验收路径。

**Non-Goals:**
- 不引入新的执行 provider 或 SDK。
- 不调整 workflow spec、callback payload、artifact manifest 的协议结构。
- 不实现自动修复网络/代理配置，只负责暴露诊断与失败原因。
- 不在本次变更中引入新的交互面，如多租户、权限系统或全新的编辑器模型。

## Decisions

### 1) 以共享诊断管线统一 Claude 调用前置检查与失败分类
**Decision**: 将 Claude 相关的 shell 环境采集、`~/.claude/settings.json` 读取、base URL / API host 解析、代理变量检查、域名预检、stderr/stdout 网络错误分类集中到共享服务中，并在 executor、validator、authoring 与 settings snapshot 中统一复用。  
**Rationale**: 当前真正影响体验的问题不是单个调用点的实现，而是调用点之间对“环境是否可用”的判断不一致。集中到单一服务可以避免每个入口各自拼接判断逻辑。  
**Alternatives**:  
- 在每个 dispatcher 内各自处理诊断：实现快，但会重复、漂移，并导致 UI 展示口径不一致。  
- 完全只依赖 Claude CLI 原始报错：排查成本高，用户很难区分代理、DNS、host 配置还是纯超时问题。  

### 2) 首字节慢启动只记为告警，真实超时仍由总超时裁决
**Decision**: `first_byte_timeout` 只负责记录 `slow_start_detected` 元数据和 UI 警告，不直接结束调用；只有整体 `timeout` 才会把调用落成 terminal failure，并且该 stop reason 优先级高于后续“未生成目标 artifact”等衍生错误。  
**Rationale**: Claude 在真实环境中经常会出现“进程已启动但长时间无输出”的情况，首字节阈值更适合作为操作提示，而不是失败裁定点。只有真实超时才能稳定对应用户可理解的“这次调用真的挂住了”。  
**Alternatives**:  
- 首字节超时立即 kill：响应更快，但会误杀仍可能成功的调用，也会让终端面板难以解释。  
- 彻底取消首字节检测：实现更简单，但会丢失慢启动信号，用户会把“无输出”误解成页面坏了。  

### 3) 运行列表采用“行动优先”分组，并把清理能力做成批量操作
**Decision**: `/runs` 页面按 `needs_attention`、`running`、其他终态分组，分别呈现“需处理 / 进行中 / 归档”；对非运行中 run 与非活动 batch 提供多选批量删除，同时保留单项删除。  
**Rationale**: 当真实使用规模上来之后，列表噪音会快速吞掉真正需要处理的项。分组加批量清理比单纯增加筛选更符合操作员的日常节奏。  
**Alternatives**:  
- 只保留筛选，不做分组：发现问题项仍需要频繁切换筛选条件。  
- 只支持单条删除：实现最简单，但无法解决历史 run / batch 堆积。  

### 4) Run Detail 默认跟随当前焦点，但允许用户固定查看历史轮次
**Decision**: 运行详情默认跟随 `current_focus` 自动更新；一旦用户主动切换到历史轮次，页面进入“手动固定”状态，直到用户明确回到当前焦点。  
**Rationale**: 自动刷新对运行监控有价值，但如果用户正在排查历史轮次，强制跳回当前焦点会严重打断分析。默认跟随 + 显式回到当前，能同时满足监控和排障。  
**Alternatives**:  
- 始终自动跟随：实时性最好，但排查历史问题非常痛苦。  
- 默认不跟随：更适合排障，但丢掉了运行中的“当前发生什么”可见性。  

### 5) 文档基线同步被视为本次变更的交付物，而不是收尾杂务
**Decision**: 将 README 的测试计数、能力描述、无 CLI 操作路径，以及 `docs/development-plan.md` 的阶段状态同步纳入任务清单与验收。  
**Rationale**: 当前文档已经落后于实现，继续忽略会直接降低下一轮 change proposal 和实现判断的质量。产品化收口如果不更新基线，实际上没有真正完成。  
**Alternatives**:  
- 先做代码，文档以后补：短期更快，但会继续扩大设计与实现偏差。  

## Risks / Trade-offs

- **[共享诊断过于严格导致误拦截]** → 仅对明确识别为 Claude 命令的调用执行预检，并返回具体失败原因与来源，便于回退或放宽策略。
- **[运行时错误优先级调整引发旧测试/旧预期漂移]** → 先统一 stop reason 规则，再同步 API 测试和 UI 文案，避免实现和断言各说各话。
- **[批量删除误操作]** → 仅允许删除非运行中项，并保留显式确认与批次历史保留要求。
- **[更多状态文案导致界面拥挤]** → 诊断信息以摘要优先，原始快照放在设置页或展开面板，不在主视图堆叠过多细节。
- **[与未归档 change 存在能力重叠]** → 在实施前优先归档或同步 `delete-run-workspace`，避免 run 删除相关 delta 分散在多个 change 中。

## Migration Plan

1. 先统一 Claude 诊断与 stop reason 语义，确保 executor / validator / authoring 共享同一套判断口径。
2. 再更新 settings、run detail、runs list 的 API 与 UI，使诊断与批量清理能力在 Studio 可见。
3. 补齐后端与前端测试，尤其覆盖慢启动、真实超时、预检失败、批量删除和历史轮次固定查看。
4. 最后刷新 README、开发计划和相关 OpenSpec 状态，并处理已完成 change 的归档/同步。

若需要回退，可先关闭或移除新的诊断展示层，保留原有命令模板与调度流程；共享诊断逻辑也可以退回为仅记录、不阻断的模式。

## Open Questions

- `delete-run-workspace` 是否应在实施前先完成归档，以免 run 清理相关要求分散在两个 active change 中。
- settings 页是否需要进一步展示 shell 环境来源细节（如区分 process env 与 shell env），还是当前 base URL / host / proxy 摘要已足够。
- 批量删除 run 时，若选中集合里混入 `running` 项，最终是整体失败还是部分成功并逐项返回错误，哪种更符合现有 API 风格。
