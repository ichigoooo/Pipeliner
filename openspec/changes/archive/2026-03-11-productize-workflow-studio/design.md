## Context

当前系统已完成 workflow spec、runtime、callback、artifact registry 与 Studio 基础视图，但 Authoring 阶段仍缺少 Claude Code 生成能力，运行自动驱动只能通过 CLI 触发，导致前端无法完成闭环。设计目标是补齐可日常使用的创作与运行路径，并保持 `workflow spec` 作为唯一真源。 
## Goals / Non-Goals

**Goals:**
- Authoring 会话支持调用 Claude Code 生成/修订草案，并记录日志与错误。 
- Studio 提供 run 自动驱动入口，减少对 CLI 依赖。 
- 支持从已发布版本或 attention 运行发起迭代会话。 
- 提升 artifact 与日志的可读性与可追溯性。 

**Non-Goals:**
- 不引入拖拽式编辑器或复杂可视化编辑模型。 
- 不引入多租户或 RBAC。 
- 不重写 runtime 状态机或协议结构。 

## Decisions

### 1) Authoring Agent 采用命令模板接入
**Decision**: 复用现有 executor/validator 的命令模板风格，引入 `authoring` 专用模板与日志记录。  
**Rationale**: 保持部署与配置一致性，避免引入新 SDK 或托管依赖。  
**Alternatives**: 直接调用外部 SDK（依赖更重、配置不统一）。 

### 2) Run Drive 作为 API 能力暴露
**Decision**: 复用现有 RunDriver，在 API 层增加 `/api/runs/{id}/drive`，前端调用驱动并显示结果。  
**Rationale**: 复用已验证的驱动逻辑，避免重复实现调度。  
**Alternatives**: 前端循环调用 dispatch（状态同步复杂，错误处理分散）。 

### 3) 迭代会话以“已有 spec + rework brief”启动
**Decision**: 从已发布版本或 attention 运行创建新会话时，以当前 spec 为基线并附带 rework brief。  
**Rationale**: 保持唯一真源与可追溯性，减少隐式变更。  
**Alternatives**: 直接修改已发布版本（破坏版本化）。 

### 4) Artifact/Log 只读预览
**Decision**: 在 Studio 中提供只读预览（manifest + storage uri + 文本/JSON 预览），不支持就地编辑。  
**Rationale**: 降低安全风险与复杂度，满足调试可读性。  
**Alternatives**: 允许修改（需要权限与审计体系）。 

## Risks / Trade-offs

- **[Authoring 生成失败]** → 提供失败原因与重试入口，保留上次草案不覆盖。 
- **[Run Drive 误触发]** → 前端确认与最大步数限制，返回 stop_reason。 
- **[日志/产物体积过大]** → 预览限制大小，超限提示下载路径。 

## Migration Plan

1. 增加 Authoring Agent API 与配置项，不影响现有手动草案保存流程。 
2. 增加 Run Drive API，前端先隐藏为实验入口。 
3. 补齐 Studio 迭代入口与 artifact/log 预览。 
4. 若新流程异常，可回退到当前“手动保存 + CLI 驱动”。 

## Open Questions

- Authoring Agent 是否需要保存完整 prompt 与响应，还是仅保存摘要与 diff。 
- 预览大小阈值与支持的 MIME 类型范围。 
