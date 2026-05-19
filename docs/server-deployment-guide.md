# 服务器部署与迁移指南

本文档用于把基因测序仪 AI 测试方案平台从临时预览环境迁移到团队服务器。当前项目包含前端 Web、FastAPI 后端、Celery Worker、PostgreSQL、Redis 和 MinIO。推荐先使用 Docker Compose 完成单机服务器部署，后续再按团队规模拆分到独立数据库、对象存储或容器平台。

## 适用场景

- 内网服务器部署，供测试工程师通过浏览器访问。
- 从当前预览环境迁移到固定服务器。
- 保留上传资料、测试条目、归口包、风险知识、验证方案导出记录和系统设置。

## 部署架构

推荐单机部署组件：

- `frontend`：React/Vite 前端，目前 Dockerfile 使用 Vite dev server，适合内网试用和验证。
- `backend-api`：FastAPI API 服务，提供 `/api/*` 接口。
- `worker`：Celery Worker，用于后续异步任务扩展。
- `postgres`：PostgreSQL + pgvector，保存业务数据。
- `redis`：Celery 队列和任务状态。
- `minio`：对象存储，保存上传资料和导出文件。

访问路径建议：

- 用户访问前端地址，例如 `http://<SERVER_IP>:5173`。
- 前端通过 `/api` 代理或反向代理访问后端 API。
- MinIO Console 仅管理员访问，例如 `http://<SERVER_IP>:9001`。

## 服务器要求

建议配置：

- CPU：4 核或以上。
- 内存：8 GB 或以上。
- 磁盘：100 GB 起步，资料池较大时按资料规模扩容。
- 系统：Linux 服务器。
- 网络：内网用户可访问前端端口，服务器可访问 AI 模型网关。

必需软件：

- Git。
- Docker Engine。
- Docker Compose Plugin。

## 代码准备

在服务器上选择部署目录，例如 `/opt/gene-test-platform`。

```bash
# 克隆代码
git clone https://github.com/cquhanxiaodan/AI_test_sysytem.git /opt/gene-test-platform

# 进入项目目录
cd /opt/gene-test-platform
```

如果服务器已经有旧版本代码：

```bash
# 进入项目目录
cd /opt/gene-test-platform

# 拉取最新代码
git pull origin master
```

## 环境变量配置

生产配置模板在 `.env.production.example`。

```bash
# 复制生产配置模板
cp .env.production.example .env
```

编辑 `.env`，至少修改以下字段：

- `DATABASE_URL`：替换 PostgreSQL 密码。
- `MINIO_ACCESS_KEY`：替换 MinIO 访问账号。
- `MINIO_SECRET_KEY`：替换 MinIO 访问密钥。
- `AI_PROVIDER`：使用本地规则时设为 `local`，接入模型时设为 `openai-compatible`。
- `AI_BASE_URL`：OpenAI 兼容模型网关地址。
- `AI_API_KEY`：模型网关 API Key。
- `AI_MODEL`：模型名称。
- `CORS_ORIGINS`：前端访问域名或服务器地址。

内网 IP 示例：

```bash
CORS_ORIGINS='["http://192.168.1.100:5173"]'
```

域名 HTTPS 示例：

```bash
CORS_ORIGINS='["https://gene-test.example.com"]'
```

## Compose 配置调整

当前 `deploy/docker-compose.yml` 默认读取 `../.env.example`。服务器部署时建议改为读取项目根目录的 `.env`。

需要把以下服务的 `env_file` 从 `../.env.example` 改为 `../.env`：

- `backend-api`
- `worker`

也可以在部署前复制模板覆盖 `.env.example`，但推荐保留 `.env.example` 作为示例文件，使用 `.env` 存放真实部署配置。

## 启动服务

```bash
# 进入项目目录
cd /opt/gene-test-platform

# 构建并启动全部服务
docker compose -f deploy/docker-compose.yml up --build -d
```

查看服务状态：

```bash
# 查看容器状态
docker compose -f deploy/docker-compose.yml ps
```

查看日志：

```bash
# 查看后端日志
docker compose -f deploy/docker-compose.yml logs backend-api

# 查看前端日志
docker compose -f deploy/docker-compose.yml logs frontend

# 查看 Worker 日志
docker compose -f deploy/docker-compose.yml logs worker
```

健康检查：

```bash
# 检查后端健康状态
curl http://127.0.0.1:8000/api/health
```

浏览器访问：

```text
http://<SERVER_IP>:5173
```

默认账号：

- 管理员：`admin / admin123`
- 测试工程师：`tester / tester123`

## 数据持久化位置

Docker Compose 使用命名卷保存核心数据：

- `postgres_data`：PostgreSQL 业务数据。
- `minio_data`：上传资料、导出文件等对象数据。
- `frontend_node_modules`：前端容器依赖缓存。

命名卷由 Docker 管理。迁移服务器时，需要同时迁移数据库数据和 MinIO 对象数据。

## 从预览环境迁移数据

当前预览环境通常使用 SQLite 和本地文件存储：

- SQLite：`backend/storage/gene-test.db`
- 本地文件：`backend/storage/`
- 系统配置：`backend/storage/system-config.json`

迁移到 Docker Compose 的 PostgreSQL + MinIO 推荐流程：

1. 在预览环境导出业务数据。
2. 在服务器启动 PostgreSQL 和 MinIO。
3. 编写一次性迁移脚本，把 SQLite 表数据写入 PostgreSQL。
4. 把 `backend/storage/` 下的文件上传到 MinIO，并更新对应存储路径。
5. 把 `system-config.json` 中的系统字典和用户配置导入服务器配置或数据库。
6. 完成后在 Web 页面抽查资料、测试条目、归口包和验证方案导出。

当前仓库尚未提供自动迁移脚本。正式迁移前，建议先冻结预览环境写入，备份 `backend/storage/`，再执行迁移。

预览环境备份命令示例：

```bash
# 进入后端目录
cd /workspace/backend

# 打包本地存储目录
tar -czf storage-backup.tgz storage
```

服务器恢复到临时本地存储模式时，可以先使用 SQLite 和本地文件存储验证数据：

```bash
REPOSITORY_BACKEND="sqlalchemy"
STORAGE_BACKEND="local"
DATABASE_URL="sqlite:///storage/gene-test.db"
LOCAL_STORAGE_ROOT="storage"
SYSTEM_CONFIG_PATH="storage/system-config.json"
```

## 资料导入目录说明

统一资料池有两种导入方式：

- `选择本地文件` 和 `选择本地文件夹`：浏览器读取用户电脑本地文件并上传到后端。
- `扫描新增资料`：后端读取服务器上的目录路径，适合管理员把文件先放到服务器目录后批量导入。

系统设置中的“统一资料池服务器导入目录”必须是后端容器内可访问的路径。使用 Docker Compose 时，需要把宿主机目录挂载进 `backend-api` 容器，才能扫描宿主机文件。

示例挂载方式：

```yaml
backend-api:
  volumes:
    - /data/gene-test-imports:/data/gene-test-imports:ro
```

页面中填写：

```text
/data/gene-test-imports
```

## 反向代理建议

内网试用可以直接访问 `http://<SERVER_IP>:5173`。正式使用建议通过 Nginx 或网关统一入口：

- `/` 转发到前端服务。
- `/api/` 转发到后端 `backend-api:8000`。
- MinIO Console 使用单独管理员域名或仅内网访问。

Nginx 示例：

```nginx
server {
    listen 80;
    server_name gene-test.example.com;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 备份策略

建议每天备份：

- PostgreSQL 数据库。
- MinIO 对象数据。
- `.env` 配置文件。
- 系统字典和运行配置。

PostgreSQL 备份示例：

```bash
# 导出数据库
docker compose -f deploy/docker-compose.yml exec postgres pg_dump -U app -d gene_test > gene_test.sql
```

MinIO 使用命名卷时，可以备份 Docker 卷或使用 MinIO 客户端同步到备份目录。

升级前建议执行：

```bash
# 备份数据库
docker compose -f deploy/docker-compose.yml exec postgres pg_dump -U app -d gene_test > gene_test-before-upgrade.sql

# 查看当前提交
git rev-parse HEAD
```

## 升级流程

```bash
# 进入项目目录
cd /opt/gene-test-platform

# 拉取最新代码
git pull origin master

# 重新构建并启动服务
docker compose -f deploy/docker-compose.yml up --build -d

# 检查服务状态
docker compose -f deploy/docker-compose.yml ps
```

后端使用 SQLAlchemy 路径启动时，会在应用启动阶段自动创建缺失表并补充部分新增字段。重大版本升级前仍建议先备份数据库。

## 常见问题

### 前端页面能打开但接口报错

检查 `CORS_ORIGINS` 是否包含当前前端访问地址。检查前端代理或 Nginx `/api/` 转发是否指向后端服务。

### 扫描新增资料找不到本地目录

扫描新增资料读取的是后端服务器或容器内目录。用户电脑本地目录应使用统一资料池页面的 `选择本地文件夹` 上传。

### AI 调用失败

检查系统设置中当前账号的 AI 配置。确认服务器能访问 `AI_BASE_URL`，并确认模型网关支持 OpenAI 兼容 `/chat/completions` 接口。

### MinIO 文件无法访问

检查 `MINIO_ENDPOINT`、`MINIO_ACCESS_KEY`、`MINIO_SECRET_KEY` 和 bucket 配置。确认 `minio` 容器运行正常。

### 数据重启后丢失

确认部署使用 `REPOSITORY_BACKEND="sqlalchemy"` 和 `STORAGE_BACKEND="minio"`，并确认 Docker Compose 命名卷存在。

## 生产加固清单

- 修改默认登录账号和密码机制，接入企业认证或正式用户管理。
- 替换 PostgreSQL、MinIO 默认密码。
- 将 `.env` 加入服务器权限保护，仅部署管理员可读。
- 使用 HTTPS 访问前端和 API。
- 限制 PostgreSQL、Redis、MinIO API 端口的公网访问。
- 配置数据库和对象存储定期备份。
- 为后端 API 配置进程守护、日志收集和资源监控。
- 前端正式部署建议改为静态构建产物托管，由 Nginx 提供服务。
