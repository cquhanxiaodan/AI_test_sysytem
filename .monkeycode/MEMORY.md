# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[测试工具资料组织偏好]
- Date: 2026-05-11
- Context: 用户讨论基因测序仪 AI 测试条目与测试方案 MVP 工具时提出
- Instructions:
  - 项目资料采用统一资料池方式管理，避免每个项目独立上传资料。
  - 多项目通过资料标签、适用范围、权限和项目关联来实现检索隔离与复用。
  - 普通用户可上传资料并填写标签，系统执行重复资料判断，管理员审核通过后资料进入可用资料池。

[测试工具 MVP 基线]
- Date: 2026-05-11
- Context: 用户确认基因测序仪 AI 测试条目与验证方案 MVP 的初版分类和模板口径
- Instructions:
  - 子系统分类目录 V1 采用一级系统域加二级子系统结构，覆盖算法和软件之外的仪器子系统及整机系统。
  - 验证方案模板 V1 采用示例 Word 的结构，包括文档履历、概述、DUT 描述、参考文档、测试项目列表、测试项目详情。
  - 测试项目详情固定采用测试目的/测试标准、测试方法/原理、测试工具、测试步骤、测试连接图或照片、测试记录、需求符合性和 BUG 信息的 7 段式结构。
  - 测试方案类文档需要按测试项目拆分为条目资产，并对每个测试条目分别映射测试对象、测试层级、测试类型、主子系统、关联子系统和分类依据。
  - 测试条目拆分后需要建立变更归口与测试集合关联，例如 RFID 变更应能汇总推荐装配、初始化、读取、写入、安规 EMC 等相关测试。

[项目启动与验证方式]
- Date: 2026-05-12
- Context: Agent 在执行 MVP 工程骨架搭建时发现
- Category: 构建方法
- Instructions:
  - 完整本地开发环境通过 `docker compose -f deploy/docker-compose.yml up --build` 启动。
  - 后端测试在 `backend` 目录执行 `pytest`。
  - 前端使用 Vite，开发服务器需保留 `server.allowedHosts` 中的 `.monkeycode-ai.online`，并通过 `/api` 代理到后端。

[持续实施偏好]
- Date: 2026-05-12
- Context: 用户要求后续按任务清单持续向后推进
- Instructions:
  - 用户希望 Agent 按既定实施计划持续实现后续任务。
  - 遇到明确阻塞、需求冲突或需要用户决策的事项时再暂停说明。

[增强后的导出与存储方式]
- Date: 2026-05-12
- Context: Agent 在执行 MVP 后续增强时发现
- Category: 代码模式
- Instructions:
  - 验证方案 Word 导出使用 `docxtpl` 渲染，默认模板路径为 `templates/validation-plan-v1.docx`。
  - 文件内容通过 `app.core.storage.StorageBackend` 访问，当前实现为 `LocalStorageBackend`，根目录由 `local_storage_root` 配置。
  - 后续接入 MinIO 时优先替换 storage backend，业务模块继续使用 `put_bytes` 和 `get_bytes` 接口。
