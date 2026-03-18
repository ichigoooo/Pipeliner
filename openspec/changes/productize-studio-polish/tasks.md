## 1. Claude 诊断与运行时语义收口

- [x] 1.1 统一 executor、validator、authoring 的 Claude 环境采集、host 解析、代理诊断与网络错误分类逻辑
- [x] 1.2 调整首字节慢启动与整体超时的裁定顺序，确保 timeout stop reason 优先于衍生的 artifact 缺失错误
- [x] 1.3 为 Claude 调用元数据补充慢启动与预检失败字段，并在 API 中稳定返回

## 2. Studio 运行体验优化

- [x] 2.1 更新 `/runs` 列表分组逻辑，突出需处理项并支持非运行中 run 的批量删除
- [x] 2.2 更新 batch 列表与详情，支持已结束 batch 的批量清理并保留 deleted run 历史标记
- [x] 2.3 更新 `/runs/[run_id]` 详情，支持“跟随当前焦点 / 固定历史轮次”切换，并展示排队、无输出、慢启动与失败摘要

## 3. 设置页与 Authoring 诊断可见性

- [x] 3.1 扩展 settings snapshot 和 `/settings` 页面，展示 Claude base URL、API host、proxy 摘要及来源
- [x] 3.2 将共享诊断逻辑接入 authoring 失败路径，返回可操作的错误说明且不覆盖现有草案
- [x] 3.3 补充相关国际化文案与原始快照字段，保证前后端口径一致

## 4. 测试与文档基线同步

- [x] 4.1 修正并补充后端测试，覆盖慢启动、真实超时、预检失败、批量删除与 authoring 诊断
- [x] 4.2 补充前端测试，覆盖 runs 分组、批量删除、run detail 焦点固定、settings 诊断展示
- [x] 4.3 更新 README、`docs/development-plan.md` 与必要的 Studio 使用说明，使文档反映最新产品基线
- [x] 4.4 归档或同步已完成的 `delete-run-workspace` change，避免 run 清理要求长期漂移
