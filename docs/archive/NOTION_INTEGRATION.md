# Notion Integration

## Notion API Token
真实 Token 不应写入仓库。请在本地 `.env` 中配置 `NOTION_API_KEY`，并确保泄露过的 Token 已在 Notion 后台轮换。

## Hermès Dashboard 项目页面
- 项目概览: https://www.notion.so/Herm-s-Dashboard-34d1ed0778ad81da88a4c7c3e6c89598

## 任务页面 (Task 4.1-4.4)
- Task 4.1: 34d1ed07-78ad-81e2-bd66-ee5b79fa1592
- Task 4.2: 34d1ed07-78ad-8101-92bd-f3ef7c17c78d
- Task 4.3: 34d1ed07-78ad-8136-aafa-f6ba7d459001
- Task 4.4: 34d1ed07-78ad-8192-960d-e499a1697502

## 已知问题
- Notion API 2025-09-03 版本：向现有页面添加子块时报 validation_error
- 原因：这些页面可能是在旧版 API 创建的，schema 不兼容
- 临时解决方案：直接在 Notion 手动勾选，或创建新的数据库页面

## API 注意事项
- database 的 properties 在 data_source 而非 database 本身
- 添加/修改属性必须 PATCH /v1/data_sources/{id}
- 创建页面用 parent.database_id，查询用 data_source_id
