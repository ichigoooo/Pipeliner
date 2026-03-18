## 1. Delete Run Backend

- [x] 1.1 在 `RunService` 与 `WorkspaceManager` 中增加 run 永久删除能力，并禁止删除 `running` run
- [x] 1.2 新增 `DELETE /api/runs/{run_id}`，返回删除结果并正确处理回滚/提交
- [x] 1.3 扩展 batch 详情接口，返回 `run_deleted` 以保留已删除 run 的历史行

## 2. Studio UI

- [x] 2.1 在运行列表中为非运行中 run 增加删除入口、确认交互和刷新逻辑
- [x] 2.2 在运行详情页增加删除入口，并在成功后返回运行列表
- [x] 2.3 在 batch 详情页展示“run 已删除”状态并禁用相关操作

## 3. Validation

- [x] 3.1 增加后端 API 测试，覆盖删除成功、删除运行中失败、batch 历史保留和 workspace 清理
- [x] 3.2 增加前端测试，覆盖运行列表/运行详情删除和 batch 已删除展示
