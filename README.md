# 基因测序仪 AI 测试方案平台

面向基因测序仪测试工程师的内部 MVP，用于沉淀统一资料池、测试条目资产、测试归口包和风险知识源，并辅助生成验证方案 Word 草稿。

## 当前工程结构

- `backend/`：FastAPI API 服务，包含健康检查和后续业务模块扩展点。
- `worker/`：Celery Worker，用于文档解析、AI 编排、向量化等异步任务。
- `frontend/`：React + TypeScript + Vite + Ant Design 前端工作台。
- `deploy/`：Docker Compose、本地数据库和基础设施初始化脚本。
- `templates/`：验证方案 Word 模板目录。
- `.monkeycode/specs/gene-sequencer-ai-test-mvp/`：需求、架构、API、AI Schema、实施计划和任务清单。

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

## 持久化配置

`.env.example` 默认面向 Docker Compose，使用 PostgreSQL 和 MinIO：

```bash
# 使用 SQLAlchemy repository 写入数据库
REPOSITORY_BACKEND="sqlalchemy"

# 使用 MinIO 保存上传资料和导出文件
STORAGE_BACKEND="minio"
```

单独运行后端测试时，默认代码配置仍使用内存仓库和本地文件存储，方便在没有 PostgreSQL、MinIO 或 Docker 的环境中快速验证。

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
