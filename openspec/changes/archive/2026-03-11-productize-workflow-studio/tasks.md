## 1. Authoring Agent 后端接入

- [x] 1.1 在配置中新增 authoring agent 命令模板与超时等参数
- [x] 1.2 实现 Authoring Agent 服务：调用 Claude Code 并返回新草案 spec
- [x] 1.3 为生成请求记录审计日志（耗时、结果、错误）
- [x] 1.4 增加 Authoring 生成 API（/api/authoring/sessions/{id}/generate 或 continue 增强）

## 2. 迭代会话与来源追踪

- [x] 2.1 增加从已发布版本创建会话的后端入口
- [x] 2.2 增加从 attention 运行创建会话的后端入口（携带 rework brief）
- [x] 2.3 会话/草案存储来源信息并在详情接口返回
- [x] 2.4 前端增加“从版本迭代/从 attention 迭代”的入口与提示

## 3. Run Drive 自动调度

- [x] 3.1 增加 /api/runs/{run_id}/drive API，复用 RunDriver 并返回摘要
- [x] 3.2 前端 Run 详情增加“自动驱动/继续驱动”按钮与结果展示
- [x] 3.3 补充 run drive API 与前端交互测试

## 4. Artifact 与日志可读性

- [x] 4.1 增加 artifact 与 log 预览 API（大小限制与类型判断）
- [x] 4.2 前端增加 artifact/log 预览面板与超限提示
- [x] 4.3 补充 artifact 预览与日志预览测试

## 5. 端到端与文档

- [x] 5.1 增加 authoring 生成、发布、运行、驱动与迭代的 E2E 测试用例
- [x] 5.2 更新 README 与 Studio 使用说明（无 CLI 路径）
