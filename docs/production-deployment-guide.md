# 生产部署专用指南

本文档面向长期运行的团队服务器部署。目标是把基因测序仪 AI 测试方案平台部署为稳定的内网 Web 应用，并保留数据库、对象存储、系统配置、上传资料和导出文件。

## 推荐架构

生产环境推荐使用单机 Docker Compose 起步，前端由 Nginx 托管静态构建产物，后端以 FastAPI 服务方式运行，数据层使用 PostgreSQL、Redis 和 MinIO。

组件职责：

- `nginx`：统一 Web 入口，提供前端静态文件和 `/api/` 反向代理。
- `backend-api`：FastAPI 后端，提供业务 API、认证、资料池、测试资产、需求分析和验证方案导出。
- `worker`：Celery Worker，用于异步任务扩展。
- `postgres`：业务数据库。
- `redis`：Celery broker 和结果存储。
- `minio`：上传资料、导出 Word、附件和解析产物对象存储。

推荐访问路径：

- 用户访问：`https://gene-test.example.com`
- API 入口：`https://gene-test.example.com/api/`
- MinIO Console：仅管理员内网访问，建议使用单独地址或通过安全组限制。

## 服务器要求

建议配置：

- 系统：Ubuntu 22.04 LTS 或 Ubuntu 24.04 LTS。
- CPU：4 核起步，推荐 8 核。
- 内存：8 GB 起步，推荐 16 GB。
- 磁盘：100 GB 起步，资料池较大时使用独立数据盘。
- 网络：固定内网 IP，正式使用建议绑定内网域名。

必需软件：

- Git。
- Docker Engine。
- Docker Compose Plugin。
- Nginx，若选择宿主机 Nginx 作为统一入口。

## 目录规划

推荐将代码、数据和备份拆分到固定目录：

```text
/opt/gene-test-platform/
├── app/                  # 项目代码
├── data/
│   ├── postgres/         # PostgreSQL 数据，使用 bind mount 时启用
│   ├── minio/            # MinIO 对象数据，使用 bind mount 时启用
│   ├── redis/            # Redis 数据，可选
│   └── imports/          # 统一资料池服务器导入目录
├── backups/              # 数据库、对象存储和配置备份
└── logs/                 # 宿主机日志，可选
```

如果继续使用 Docker 命名卷，需要重点备份 `postgres_data` 和 `minio_data`。如果使用 bind mount，建议把 `data/` 放在有备份策略的数据盘上。

## 代码部署

```bash
# 创建部署目录
mkdir -p /opt/gene-test-platform

# 克隆项目代码
git clone https://github.com/cquhanxiaodan/AI_test_sysytem.git /opt/gene-test-platform/app

# 进入项目目录
cd /opt/gene-test-platform/app
```

已有部署升级时：

```bash
# 进入项目目录
cd /opt/gene-test-platform/app

# 拉取最新代码
git pull origin master
```

## 生产环境变量

以 `.env.production.example` 为模板创建生产配置：

```bash
# 进入项目目录
cd /opt/gene-test-platform/app

# 创建生产配置
cp .env.production.example .env
```

至少替换这些配置：

- `DATABASE_URL`：替换数据库用户、密码、主机和库名。
- `MINIO_ACCESS_KEY`：替换为生产访问账号。
- `MINIO_SECRET_KEY`：替换为生产访问密钥。
- `AI_PROVIDER`：使用本地规则时设为 `local`，接入模型网关时设为 `openai-compatible`。
- `AI_BASE_URL`：OpenAI 兼容模型网关地址。
- `AI_API_KEY`：模型网关 API Key。
- `AI_MODEL`：模型名称。
- `CORS_ORIGINS`：正式访问域名。

示例：

```env
APP_NAME="Gene Sequencer AI Test API"
APP_VERSION="0.1.0"
ENVIRONMENT="production"
REPOSITORY_BACKEND="sqlalchemy"
STORAGE_BACKEND="minio"

DATABASE_URL="postgresql+psycopg://app:CHANGE_ME@postgres:5432/gene_test"
REDIS_URL="redis://redis:6379/0"
CELERY_BROKER_URL="redis://redis:6379/1"
CELERY_RESULT_BACKEND="redis://redis:6379/2"

MINIO_ENDPOINT="minio:9000"
MINIO_ACCESS_KEY="CHANGE_ME"
MINIO_SECRET_KEY="CHANGE_ME"
MINIO_SECURE="false"
MINIO_BUCKET="gene-test-documents"

AI_PROVIDER="openai-compatible"
AI_BASE_URL="https://your-model-gateway.example.com/v1"
AI_API_KEY="CHANGE_ME"
AI_MODEL="your-model-name"
AI_TIMEOUT_SECONDS="60"

CORS_ORIGINS='["https://gene-test.example.com"]'
```

`.env` 应仅允许部署管理员读取：

```bash
# 限制配置文件权限
chmod 600 .env
```

## 生产 Compose 建议

当前 `deploy/docker-compose.yml` 偏开发和内网试用：前端运行 Vite dev server，后端带 `--reload`，并挂载源代码。生产环境建议新增 `deploy/docker-compose.prod.yml`，或者在服务器上维护同等内容的生产 Compose 文件。

生产 Compose 应满足：

- `backend-api` 和 `worker` 读取 `../.env`。
- 后端启动命令关闭 `--reload`。
- 前端先执行 `npm run build` 生成 `frontend/dist`，由 Nginx 托管。
- PostgreSQL、MinIO、Redis 使用命名卷或 bind mount 持久化。
- 服务器导入目录挂载到 `backend-api`，页面中填写容器内路径。
- PostgreSQL、Redis、MinIO API 端口仅对服务器本机或内网开放。

生产 Compose 骨架示例：

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: CHANGE_ME
      POSTGRES_DB: gene_test
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d gene_test"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: CHANGE_ME
      MINIO_ROOT_PASSWORD: CHANGE_ME
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend-api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    env_file:
      - ../.env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - /opt/gene-test-platform/data/imports:/data/imports:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_started

  worker:
    build:
      context: ..
      dockerfile: worker/Dockerfile
    env_file:
      - ../.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_started

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

启动命令：

```bash
# 进入项目目录
cd /opt/gene-test-platform/app

# 启动生产服务
docker compose -f deploy/docker-compose.prod.yml up --build -d
```

## 前端静态构建

生产环境推荐构建 `frontend/dist`，再由 Nginx 托管。

```bash
# 进入前端目录
cd /opt/gene-test-platform/app/frontend

# 安装依赖
npm install

# 构建静态文件
npm run build
```

构建产物位置：

```text
/opt/gene-test-platform/app/frontend/dist
```

升级时每次拉取代码后重新执行 `npm install` 和 `npm run build`。

## Nginx 配置

宿主机 Nginx 推荐配置：

```nginx
server {
    listen 80;
    server_name gene-test.example.com;

    client_max_body_size 500m;

    root /opt/gene-test-platform/app/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

如果 `backend-api` 只暴露在 Docker 网络中，宿主机 Nginx 需要能访问后端端口。上面的生产 Compose 示例已使用仅本机监听：

```yaml
backend-api:
  ports:
    - "127.0.0.1:8000:8000"
```

启用 HTTPS 时，将 `server_name` 替换为正式域名，并配置企业证书或内网 CA 证书。

## 资料导入目录

统一资料池有两类入口：

- `选择本地文件` 和 `选择本地文件夹`：浏览器读取用户电脑文件并上传。
- `扫描新增资料`：后端读取服务器目录，适合管理员把大批文件先放入服务器。

生产环境建议使用固定导入目录：

```text
/opt/gene-test-platform/data/imports
```

Compose 挂载到后端容器：

```yaml
backend-api:
  volumes:
    - /opt/gene-test-platform/data/imports:/data/imports:ro
```

页面中填写容器内路径：

```text
/data/imports
```

## 启动检查

```bash
# 查看容器状态
docker compose -f deploy/docker-compose.prod.yml ps

# 查看后端日志
docker compose -f deploy/docker-compose.prod.yml logs backend-api

# 查看 Worker 日志
docker compose -f deploy/docker-compose.prod.yml logs worker

# 检查健康接口
curl http://127.0.0.1:8000/api/health
```

浏览器访问：

```text
https://gene-test.example.com
```

首次上线后检查：

- 管理员账号可以登录。
- 普通测试工程师账号可以登录。
- 统一资料池可以上传文件。
- 管理员可以发布资料。
- 测试条目、归口包和风险知识可以正常展示。
- 验证方案可以导出 Word。
- 系统设置中的 AI 配置可以按用户保存。
- 服务器导入目录可以扫描容器内 `/data/imports`。

## 备份策略

建议至少备份以下内容：

- PostgreSQL 数据库。
- MinIO 对象数据。
- `.env` 生产配置。
- Nginx 配置。
- `backend/templates/validation-plan-v1.docx`。
- 服务器资料导入目录。

数据库备份示例：

```bash
# 创建备份目录
mkdir -p /opt/gene-test-platform/backups

# 导出 PostgreSQL 数据库
docker compose -f deploy/docker-compose.prod.yml exec postgres pg_dump -U app -d gene_test > /opt/gene-test-platform/backups/gene_test-$(date +%F).sql
```

MinIO 使用命名卷时，可备份 Docker 卷或使用 MinIO Client 同步对象。使用 bind mount 时，备份 `/opt/gene-test-platform/data/minio`。

建议保留策略：

- 最近 7 天每日备份。
- 最近 4 周每周备份。
- 最近 6 个月每月备份。

## 升级流程

```bash
# 进入项目目录
cd /opt/gene-test-platform/app

# 记录当前版本
git rev-parse HEAD

# 备份数据库
docker compose -f deploy/docker-compose.prod.yml exec postgres pg_dump -U app -d gene_test > /opt/gene-test-platform/backups/gene_test-before-upgrade.sql

# 拉取最新代码
git pull origin master

# 重新构建前端
cd frontend
npm install
npm run build

# 回到项目根目录
cd ..

# 重建后端和 Worker
docker compose -f deploy/docker-compose.prod.yml up --build -d

# 查看服务状态
docker compose -f deploy/docker-compose.prod.yml ps
```

后端使用 SQLAlchemy 路径启动时，会在应用启动阶段自动创建缺失表并补充部分新增字段。重大版本升级前应先备份数据库和 MinIO 数据。

## 回滚流程

```bash
# 进入项目目录
cd /opt/gene-test-platform/app

# 切回上一个确认可用的提交
git checkout <GOOD_COMMIT_SHA>

# 重新构建前端
cd frontend
npm install
npm run build

# 回到项目根目录
cd ..

# 重建服务
docker compose -f deploy/docker-compose.prod.yml up --build -d
```

如果升级已修改数据库结构，需要根据备份恢复数据库。恢复前先停止服务，确认备份文件和目标数据库匹配。

## 生产安全清单

- 替换 PostgreSQL、MinIO、应用默认账号密码。
- `.env` 使用 `chmod 600` 保护。
- Nginx 开启 HTTPS。
- 仅对内网开放 Web 入口。
- PostgreSQL、Redis 和 MinIO API 端口限制为服务器本机或可信内网。
- MinIO Console 仅管理员可访问。
- 定期备份 PostgreSQL 和 MinIO。
- 升级前保存当前 Git commit 和数据库备份。
- AI API Key 仅保存在服务器 `.env` 或用户个人系统设置中。
- 服务器导入目录只挂载后端需要读取的路径。

## 常见问题

### 页面打开后接口报错

检查 `CORS_ORIGINS` 是否包含正式访问域名，并确认 Nginx `/api/` 转发到后端 `8000` 端口。

### 上传大文件失败

检查 Nginx `client_max_body_size`，并确认后端、MinIO 和磁盘空间正常。

### 扫描新增资料没有文件

确认页面填写的是容器内路径，例如 `/data/imports`。确认宿主机目录已挂载到 `backend-api` 容器。

### AI 调用失败

检查当前登录用户的系统设置 AI 配置。确认服务器能访问 `AI_BASE_URL`，并确认模型网关兼容 OpenAI `/chat/completions`。

### 重启后数据丢失

确认使用 `REPOSITORY_BACKEND="sqlalchemy"` 和 `STORAGE_BACKEND="minio"`。确认 PostgreSQL 和 MinIO 使用了持久化卷或 bind mount。
