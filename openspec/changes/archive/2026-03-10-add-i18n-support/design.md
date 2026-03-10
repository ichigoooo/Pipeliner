## Context

Pipeliner Studio 前端使用 Next.js 15 + React 19 + TypeScript 构建。当前所有 UI 文本都是硬编码的中文，没有国际化支持。项目使用 Zustand 进行状态管理，TanStack Query 进行数据获取。

需要引入一个轻量级、与 Next.js 兼容的 i18n 解决方案，支持：
- 客户端语言切换（Settings 页面）
- 翻译键值管理
- 语言偏好持久化
- TypeScript 类型支持

## Goals / Non-Goals

**Goals:**
- 支持英语 (en) 和中文 (zh) 两种语言
- 所有 UI 文本可翻译
- Settings 页面添加语言选择器
- 语言偏好持久化到 localStorage
- 默认语言自动检测（浏览器语言）

**Non-Goals:**
- 服务端渲染 (SSR) 国际化（当前使用静态导出）
- 日期/数字/货币格式化
- RTL 语言支持
- 翻译管理系统集成

## Decisions

### 1. 使用 next-intl 作为 i18n 库

**选择**: `next-intl` v3.x

**理由**:
- 专为 Next.js 设计，API 简洁
- 完整的 TypeScript 支持
- 支持客户端组件（App Router）
- 轻量级，无额外依赖

**替代方案**:
- `react-i18next`: 功能更全但配置复杂
- 自研方案: 维护成本高

### 2. 翻译文件结构

```
web/src/i18n/
├── config.ts           # 配置和类型
├── provider.tsx        # I18nProvider 封装
├── messages/
│   ├── en.json         # 英文翻译
│   └── zh.json         # 中文翻译
└── use-language.ts     # 语言切换 Hook
```

**理由**: 扁平化结构便于维护，JSON 格式便于非开发者编辑。

### 3. 语言状态管理

使用 Zustand store 管理语言状态，结合 localStorage 持久化。

**理由**: 与现有状态管理方案一致，避免引入新的全局状态。

### 4. 翻译键命名规范

采用 `page.component.element` 层级命名，例如：
- `settings.language.title`
- `settings.language.description`
- `sidebar.navigation.workflows`

**理由**: 清晰的命名空间避免冲突，便于查找。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 翻译键遗漏 | 使用 TypeScript 类型检查，所有键必须存在 |
| 翻译文件体积 | 仅加载当前语言，按需加载 |
| 新功能翻译滞后 | 开发流程要求：新 UI 必须同时添加中英文 |

## Migration Plan

1. **Phase 1**: 搭建 i18n 基础设施（config, provider, hooks）
2. **Phase 2**: 提取 Settings 页面文本（作为试点）
3. **Phase 3**: 提取所有页面和组件文本
4. **Phase 4**: 验证和测试

## Open Questions

- 是否需要支持语言热切换（不刷新页面）？
  - 决定：是，使用 Zustand + next-intl 的客户端切换
