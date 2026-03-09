# Pipeliner 设计文档审查反馈

**审查日期**: 2026-03-08
**审查范围**: docs/ 目录下全部 5 份设计文档
**文档版本**: V1 设计阶段

---

## 一、总体评价

设计文档整体质量较高，具有以下优点：

- **结构清晰**: 每份文档都遵循统一格式（角色定位 → 设计目标 → 原则 → 结构 → 字段定义）
- **职责边界明确**: Workflow Spec、Callback Payload、Artifact Manifest、Runtime Guards 之间分工清晰
- **V1 克制原则**: 不提前过度设计，优先保证最小可用闭环
- **文档间引用得当**: 形成了完整的设计体系

---

## 二、一致性 Issues

### 1. `shape` 字段定义不一致 ⚠️

**问题描述**:

| 文档 | 字段 | 枚举值 |
|------|------|--------|
| `workflow-spec-design.md` | `shape` | `text`, `json`, `file`, `directory`, `collection` |
| `artifact-manifest-design.md` | `kind` | `file`, `directory`, `collection` |

**影响**: 节点合同层与物理存储层的形态描述存在重叠但不一致，可能导致理解混淆。

**建议**:
- 明确区分 `shape`（节点合同层的形态描述）和 `kind`（artifact 物理形态）
- 或在文档中补充两者的映射关系表

---

### 2. 版本号格式不一致 ⚠️

**问题描述**: 示例中混用两种版本格式：

```json
// workflow-spec-design.md
"version": "0.1.0"  // 语义化版本

// artifact-manifest-design.md
"version": "v1"     // 简单版本
```

**建议**:
- 统一使用语义化版本（`0.1.0`）作为 workflow 版本
- 使用简单版本（`v1`, `v2`）作为 artifact 版本
- 在文档中明确两种格式的使用场景

---

## 三、潜在设计缺陷

### 3. 依赖一致性校验规则缺失 ⚠️⚠️

**位置**: `workflow-spec-design.md` 第 359-360 行

**问题描述**: 文档提到应通过 lint 检查 `depends_on` 与 `inputs.from` 的一致性，但未定义：
- 不一致时的处理策略（警告 vs 错误）
- 哪个字段优先（当两者冲突时）
- 循环依赖的检测规则

**建议**: 补充依赖图合法性校验的具体规则，例如：

```
Lint 规则（建议）:
1. [ERROR] inputs.from 引用的节点必须在 depends_on 中声明
2. [WARNING] depends_on 中声明的节点未被任何 inputs.from 引用
3. [ERROR] 检测到循环依赖: A → B → C → A
```

---

### 4. Runtime Guards 过度简化 ⚠️

**位置**: `runtime-guards-design.md` 第 116-133 行

**问题描述**: `blocked_requires_manual` 和 `failure_requires_manual` 被固定为 `true`，意味着：
- 无法配置自动重试策略
- 所有失败都需要人工介入

**建议**:
- 虽然 V1 保持克制，但建议预留配置接口
- 或在文档中说明未来扩展计划（如 V2 支持 `auto_retry` 策略）

---

## 四、完整性 Gaps

### 5. 错误处理与恢复机制设计缺失 ⚠️⚠️

**问题描述**: 所有文档都未详细说明以下场景的处理：

| 场景 | 当前状态 | 建议补充 |
|------|----------|----------|
| Artifact 存储失败 | 未定义 | 补充重试策略和降级方案 |
| Callback 网络超时 | 未定义 | 补充幂等重试机制 |
| Callback 丢失 | 未定义 | 补充心跳检测和超时判定 |
| 磁盘空间不足 | 未定义 | 补充前置检查 |

**建议**: 补充最小错误处理契约，即使 V1 只是本地文件系统。

---

### 6. Workflow Spec `defaults` 字段内容空洞 ⚠️

**位置**: `workflow-spec-design.md` 第 543-565 行

**问题描述**: 虽然 `defaults` 被定义为可选字段，但未定义任何具体配置项。

**建议**: 至少定义 V1 可用的最小默认配置集：

```json
{
  "defaults": {
    "timeout": "30m",
    "max_rework_rounds": 3,
    "gate": {
      "mode": "all_validators_pass"
    }
  }
}
```

---

### 7. Skill 引用契约缺失 ⚠️⚠️

**问题描述**: 多个文档提到 `skill` 绑定，但未定义 Skill 引用的格式：

```
不确定的引用格式:
- "draft-wechat-article"                    // 简单字符串
- "skill://draft-wechat-article@v1.2.0"     // URI 格式
- {"name": "draft-wechat-article", "version": "v1.2.0"}  // 结构化
```

**建议**: 补充 Skill Reference 的最小规范，例如：

```json
{
  "skill": {
    "name": "draft-wechat-article",
    "version": "v1.2.0",
    "source": "local"  // 或 "registry", "git"
  }
}
```

---

## 五、命名与术语建议

### 8. `gate` vs `acceptance` 术语边界模糊 ⚠️

**问题描述**:
- `acceptance` 包含 `done_means` 和 `pass_condition`
- `gate` 包含 `mode`

用户可能不清楚两者的边界。

**建议**: 在文档中增加对比说明：

```
acceptance = 定义"什么是完成"（语义层面）
gate       = 定义"如何判断是否通过"（策略层面）
```

---

### 9. `archetype` 枚举值未定义 ⚠️

**位置**: `workflow-spec-design.md` 第 343-344 行

**问题描述**: 提到可使用 `custom`，但未列出 V1 支持的预置原型列表。

**建议**: 明确列出 V1 最小原型集：

```
V1 预置原型:
- draft-content      // 内容生成
- review-content     // 内容审校
- generate-json      // JSON 生成
- structured-extract // 结构化提取
- custom             // 自定义
```

---

## 六、协议兼容性考虑

### 10. Schema Version 演进策略未明确 ⚠️

**问题描述**: 所有协议都有 `schema_version`，但未说明：
- 版本号变更规则（主版本不兼容？次版本兼容？）
- 旧版本协议的兼容支持周期
- 迁移策略

**建议**: 补充版本演进基本规则，例如：

```
版本规则（建议）:
- 主版本（v1 → v2）: 不兼容变更，需要显式迁移
- 次版本（v1.0 → v1.1）: 向后兼容，新增可选字段
- 补丁版本（v1.0.0 → v1.0.1）: 文档修正，无协议变更
```

---

### 11. `extensions` 字段使用规范缺失 ⚠️

**问题描述**: 多个文档都有 `extensions`，警告不要变成"杂项收纳盒"，但未给出使用规范。

**建议**: 定义 `extensions` 的最小使用契约：

```json
{
  "extensions": [
    {
      "name": "pipeliner.ui",
      "version": "v1",
      "data": { ... }
    }
  ]
}
```

---

## 七、具体文档建议

### `pipeliner-agent-orchestrator-design.md`

**12. 文档过长建议拆分** 📋

当前 1162 行，建议拆分为：

| 新文档 | 内容范围 |
|--------|----------|
| `pipeliner-storage-layout.md` | 第 583-823 行（交付物流转与运行工作目录）|
| `pipeliner-runtime-callback.md` | 第 861-1058 行（运行反馈与 API 汇报机制）|

---

**13. 结论表述不一致** 📋

**位置**: 第 1119-1126 行

**问题**: 说"当前主要阻塞设计已经基本收敛"，但第 12 节仍有大量"待确认事项"。

**建议**: 更新结论表述为：
> "核心协议设计已收敛，部分实现细节和演进方向待后续版本确认"

---

### `node-callback-payload-design.md`

**14. `rework_brief.must_fix` 边界情况未定义** 📋

**问题**: 当 `must_fix` 为空数组时如何处理？

**建议**: 明确以下规则：
- `must_fix` 为空数组 → 视为无返工需求，等同于 `pass`
- `must_fix` 字段缺失 → 视为格式错误

---

### `artifact-manifest-design.md`

**15. `storage.uri` 格式规范不明确** 📋

**问题**: 路径格式建议更加明确：
- 是绝对路径还是相对路径？
- 相对于什么基准？
- 是否允许 `file://` URI scheme？

**建议**: 补充规范：

```json
{
  "storage": {
    "backend": "local_fs",
    "uri": "runs/pipeline-slug/run_id/artifacts/artifact@v1/payload",
    "uri_is_relative_to": "WORKSPACE_ROOT"
  }
}
```

---

## 八、文档间交叉引用建议

建议增加以下显式引用：

| 从文档 | 引用到 | 说明 |
|--------|--------|------|
| `workflow-spec-design.md` | `artifact-manifest-design.md` | 说明 `outputs` 如何对应到 artifact |
| `node-callback-payload-design.md` | `runtime-guards-design.md` | 说明 `timeout` 如何触发 guard |
| `artifact-manifest-design.md` | `node-callback-payload-design.md` | 说明 `artifact_id` 如何在 callback 中使用 |

---

## 九、优先级汇总

### 高优先级（建议 V1 解决）

| 序号 | 问题 | 影响 |
|------|------|------|
| 7 | Skill 引用契约缺失 | 协议不完整，无法实现 |
| 2 | 版本号格式不一致 | 可能导致实现混乱 |
| 3 | 依赖一致性校验规则缺失 | 可能导致运行时错误 |

### 中优先级（V1 可选，V2 必须）

| 序号 | 问题 | 影响 |
|------|------|------|
| 1 | `shape`/`kind` 定义对齐 | 概念混淆 |
| 5 | 错误恢复机制 | 系统健壮性 |
| 8 | 术语澄清 | 理解成本 |
| 10 | Schema 版本演进策略 | 长期维护 |

### 低优先级（建议优化）

| 序号 | 问题 | 影响 |
|------|------|------|
| 12 | 文档拆分 | 可读性 |
| 15 | URI 格式细化 | 实现细节 |
| 11 | 扩展字段规范 | 未来扩展 |

---

## 十、附录：设计文档清单

| 文档 | 状态 | 核心贡献 |
|------|------|----------|
| `workflow-spec-design.md` | 基本收敛 | 定义工作流规范结构 |
| `node-callback-payload-design.md` | 已收敛 | 定义节点回调协议 |
| `artifact-manifest-design.md` | 已收敛 | 定义交付物登记协议 |
| `runtime-guards-design.md` | 已收敛 | 定义运行时安全护栏 |
| `pipeliner-agent-orchestrator-design.md` | 待拆分 | 总体架构与原则 |

---

*本反馈文档由 Claude Code 生成，供设计评审参考。*
