## Why

Pipeliner Studio 目前仅支持中文界面，限制了对国际用户的使用便利性。随着项目的发展，需要提供多语言支持以满足不同地区用户的需求。通过在设置界面中切换语言，可以提升用户体验并扩大项目的适用范围。

## What Changes

- 引入 i18n（国际化）架构，支持英语和中文两种语言
- 所有用户界面文本提取为翻译键值，支持动态语言切换
- 在 Settings 页面添加语言选择器，控制全局语言状态
- 语言偏好持久化存储（localStorage）
- 默认语言根据浏览器语言自动检测，回退到英文

## Capabilities

### New Capabilities
- `i18n-core`: 核心国际化框架，包括语言检测、翻译加载、语言切换机制
- `i18n-ui-translations`: 所有 UI 组件的文本翻译（英语和中文）
- `settings-language-selector`: Settings 页面语言选择器组件

### Modified Capabilities
- `settings-page`: 在设置页面添加语言切换选项

## Impact

- **前端代码**: `web/src/` 下的所有组件需要引入翻译 Hook
- **依赖**: 需要添加 i18n 库（如 `next-intl` 或 `react-i18next`）
- **存储**: 使用 localStorage 持久化语言偏好
- **API**: 无后端改动，纯前端实现
