# 基因测序仪 AI 测试方案平台

面向基因测序仪测试工程师的内部 MVP，用于沉淀统一资料池、测试条目资产、测试归口包和风险知识源，并辅助生成验证方案 Word 草稿。

## 当前工程结构

- `backend/`：FastAPI API 服务，包含健康检查和后续业务模块扩展点。
- `worker/`：Celery Worker，用于文档解析、AI 编排、向量化等异步任务。
- `frontend/`：React + TypeScript + Vite + Ant Design 前端工作台。
- `deploy/`：Docker Compose、本地数据库和基础设施初始化脚本。
- `templates/`：验证方案 Word 模板目录。
- `docs/user-guide.md`：端到端使用说明，覆盖统一资料池、测试资产、AI 调用、需求分析和验证方案导出。
- `docs/server-deployment-guide.md`：服务器部署与迁移指南，覆盖 Docker Compose 部署、数据迁移、备份和升级。
- `.monkeycode/specs/gene-sequencer-ai-test-mvp/`：需求、架构、API、AI Schema、实施计划和任务清单。

## 主流程

MVP 主流程以统一资料池为入口：

1. 上传测试规范、验证方案、测试报告、Jira 导出或 DFMEA 文件。
2. 确认系统识别出的产品型号、子系统、文档类型和变更类型标签。
3. 管理员发布资料。
4. 系统按文档类型自动生成测试条目、测试归口包或风险知识项。
5. 测试工程师输入新需求或变更描述，系统基于测试资产和风险知识源推荐测试项。
6. 生成验证方案草稿，完整性检查后导出 Word 文件。

详细操作见 `docs/user-guide.md`。

## 项目空间

项目空间用于隔离某个产品项目的某个综合变更，例如 `G99 ECR4.0`。所有登录用户都可以在 Web 页面进入 `项目空间` 创建项目，并填写项目编码、项目名称和项目说明。创建后，项目会出现在顶部项目选择器中，统一资料池、测试资产、需求分析和验证方案都会按当前项目空间工作。

项目空间支持删除。删除时需要输入当前账号密码进行二次确认。

`项目工作台` 会基于当前项目空间展示真实统计、项目状态、推荐下一步和快捷入口。

## 自由应用

`自由应用` 提供面向当前项目空间的自由问答。用户可以选择是否使用当前项目资料库和已配置的大模型。系统会先检索项目资料、测试条目、测试归口包和风险知识源；模型已配置时会结合检索结果生成回答，模型不可用时返回本地资料命中摘要。

## 本地启动

```bash
# 启动完整开发环境
docker compose -f deploy/docker-compose.yml up --build
```

服务端口：

- 前端：`http://localhost:5173`
- 后端 API：`http://localhost:8000/api/health`
- MinIO Console：`http://localhost:9001`
- PostgreSQL：`localhost:5432`
- Redis：`localhost:6379`

## 当前预览方式

当前 MVP 是 Web 界面化应用。预览时需要同时启动后端 API 和前端开发服务器：

```bash
# 进入后端目录
cd backend

# 启动 FastAPI API
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
# 进入前端目录
cd frontend

# 启动 Vite 前端
npm run dev -- --host 0.0.0.0
```

登录账号：

- 管理员：`admin / admin123`
- 测试工程师：`tester / tester123`

## 持久化配置

`.env.example` 默认面向 Docker Compose，使用 PostgreSQL 和 MinIO：

```bash
# 使用 SQLAlchemy repository 写入数据库
REPOSITORY_BACKEND="sqlalchemy"

# 使用 MinIO 保存上传资料和导出文件
STORAGE_BACKEND="minio"
```

单独运行后端时，默认代码配置使用 SQLite 和本地文件存储，数据会保存在 `backend/storage/gene-test.db` 与 `backend/storage/` 下，重启后资料、测试条目、归口包和风险知识源会保留。后端测试会在测试用例中显式切换到内存仓库，避免测试数据互相污染。

## AI 模型接入

默认 `AI_PROVIDER="local"`，系统使用本地规则兜底。接入内网模型网关或 OpenAI 兼容服务时配置：

```bash
AI_PROVIDER="openai-compatible"
AI_BASE_URL="https://your-model-gateway.example.com/v1"
AI_API_KEY="CHANGE_ME"
AI_MODEL="your-model-name"
AI_TIMEOUT_SECONDS="20"
```

可通过 `GET /api/ai/config` 查看模型接入状态。系统采用“本地知识优先 + AI JSON 补全 + 失败回退”的调用方式：先读取统一资料池、文档切片、测试条目、测试归口包和风险知识源，再把本地候选结果交给模型补充结构化字段。调用失败、超时或输出不符合 Schema 时自动回退本地规则。

所有登录用户都可以在 Web 页面进入 `系统设置` 配置 AI 模型。页面支持填写 OpenAI 兼容接口的 Base URL、模型名称、API Key 和超时时间；API Key 只显示掩码，留空保存会保留当前值。页面保存的是当前后端进程的运行时配置，容器或服务重启后的默认值仍以环境变量为准。

当前 AI 调用任务：

| 任务 | 本地输入 | AI 输出 | 回退策略 |
| --- | --- | --- | --- |
| `document_label_extraction` | 文件名、已有标签、标签建议、文档切片 | 资料标签、置信度、依据 | 保留高置信度本地标签 |
| `requirement_parse` | 需求文本 | 测试对象、变更类型、产品型号、子系统、缺失字段 | 使用关键词和标准字段解析 |
| `test_item_split` | 文档切片、本地拆分候选 | 测试条目数组和证据 | 使用 RFID/通用启发式拆分 |
| `risk_parse` | Jira/DFMEA 原始内容、本地风险候选 | 风险项数组和证据 | 使用 CSV/文本解析 |
| `requirement_recommendation` | 需求解析、本地归口包、风险项、知识检索命中 | 必测、建议、条件触发推荐 | 使用归口包和风险项推荐 |
| `validation_plan_check` | 验证方案 JSON、本地检查结果 | 阻断项、警告、建议 | 使用本地完整性检查 |

AI 推荐必须保留本地 `source_type`、`source_id` 和 `evidence`，用于后续审核和追溯。

## 生产部署建议

生产环境使用 `.env.production.example` 作为配置模板，并替换数据库密码、MinIO 账号和访问域名。

服务器迁移和部署步骤见 `docs/server-deployment-guide.md`。

推荐组件：

- 前端 Web：React/Vite 构建产物，由 Nginx 或对象存储静态站点托管。
- 后端 API：FastAPI，建议至少 2 个进程实例。
- Worker：Celery Worker，用于后续文档解析、AI 调用和向量化任务。
- PostgreSQL：业务数据和后续 pgvector 向量索引。
- Redis：异步队列和任务状态。
- MinIO：上传资料、解析附件和导出 Word 文件。

## 单独运行后端测试

```bash
# 进入后端目录
cd backend

# 安装后端依赖
pip install --break-system-packages ".[dev]"

# 运行测试
pytest
```

## 单独运行前端

```bash
# 进入前端目录
cd frontend

# 安装前端依赖
npm install

# 启动 Vite 开发服务器
npm run dev
```
