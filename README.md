# 基因测序仪 AI 测试方案平台

面向基因测序仪测试工程师的内部 MVP，用于沉淀统一资料池、测试条目资产、测试归口包和风险知识源，并辅助生成验证方案 Word 草稿。

## 当前工程结构

- `backend/`：FastAPI API 服务，包含健康检查和后续业务模块扩展点。
- `worker/`：Celery Worker，用于文档解析、AI 编排、向量化等异步任务。
- `frontend/`：React + TypeScript + Vite + Ant Design 前端工作台。
- `deploy/`：Docker Compose、本地数据库和基础设施初始化脚本。
- `templates/`：验证方案 Word 模板目录。
- `docs/user-guide.md`：端到端使用说明，覆盖统一资料池、测试资产、AI 调用、需求分析和验证方案导出。
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

单独运行后端测试时，默认代码配置仍使用内存仓库和本地文件存储，方便在没有 PostgreSQL、MinIO 或 Docker 的环境中快速验证。

## 生产部署建议

生产环境使用 `.env.production.example` 作为配置模板，并替换数据库密码、MinIO 账号和访问域名。

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
