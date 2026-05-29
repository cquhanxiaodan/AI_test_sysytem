# 项目交接摘要

本文档用于向开发、部署、运维和业务接手人员说明当前项目状态、已完成内容、部署方式、关键决策和后续事项。

## 项目概览

项目名称：基因测序仪 AI 测试方案平台。

项目定位：面向基因测序仪测试工程师的内部 Web 工具，用于沉淀统一资料池、测试条目资产、测试归口包和风险知识源，并辅助完成需求分析、测试项推荐和验证方案 Word 草稿导出。

核心技术栈：

- 后端：FastAPI、SQLAlchemy、Celery。
- 前端：React、TypeScript、Vite、Ant Design。
- 数据库：PostgreSQL，当前本地预览可使用 SQLite。
- 队列：Redis。
- 对象存储：MinIO，当前本地预览可使用本地文件存储。
- 部署：Docker Compose，生产建议前端静态化后由 Nginx 托管。

## 仓库结构

- `backend/`：FastAPI API 服务，包含认证、资料池、测试资产、需求分析、风险、反馈、验证方案等业务模块。
- `frontend/`：React + Vite 前端工作台。
- `worker/`：Celery Worker，用于异步任务扩展。
- `deploy/`：Docker Compose、本地数据库和基础设施初始化脚本。
- `docs/user-guide.md`：端到端用户操作说明。
- `docs/server-deployment-guide.md`：服务器部署与迁移指南，偏内网试用和迁移。
- `docs/production-deployment-guide.md`：生产部署专用指南，偏长期运行、Nginx、备份、升级和回滚。
- `.monkeycode/MEMORY.md`：项目规则、用户偏好和关键业务决策记忆。
- `.monkeycode/specs/gene-sequencer-ai-test-mvp/`：MVP 需求、设计、API、AI Schema 和实施任务资料。

## 当前主流程

1. 用户在统一资料池上传测试规范、验证方案、测试报告、Jira 导出或 DFMEA 文件。
2. 系统识别并推荐产品型号、子系统、模块、文档类型和变更类型标签。
3. 用户确认标签，管理员发布资料。
4. 资料发布后生成测试条目资产或风险知识项。
5. 测试条目审核发布后自动形成或更新测试归口包。
6. 测试工程师输入新需求或变更描述，系统基于已发布测试条目、归口包和风险知识推荐测试项。
7. 用户审核推荐项，确认后生成验证方案草稿。
8. 系统执行完整性检查并导出 Word 验证方案。

## 已完成能力

### 统一资料池

- 支持本地文件上传。
- 支持本地文件夹批量上传，浏览器读取用户电脑目录后上传到后端。
- 支持服务器目录扫描导入，扫描后端容器内可访问路径。
- 上传和扫描导入后继续走标签识别、补标签、去重和管理员审核发布流程。
- 资料标签使用系统字典下拉，减少自由输入导致的标签不一致。

### 系统字典和设置

- 系统字典为全局共享配置，仅管理员可维护。
- 普通用户可以只读查看系统字典摘要。
- 支持主子系统、关联子系统、测试层级、测试类型、文档类型、变更类型等字典。
- 支持“子系统-模块联动字典”，例如电子子系统下保留 `RFID` 作为模块。
- AI 模型配置按当前登录用户独立保存。
- 统一资料池服务器导入目录按当前登录用户独立保存。

### 测试条目和归口包

- 资料发布后只生成测试条目资产，不直接生成归口包。
- 测试条目审核发布后，再自动形成或更新归口包。
- 测试条目保存完整字段，包括目的、方法、工具、步骤、记录模板、证据和原始块。
- 测试条目包含主子系统和模块字段。
- 测试类型最终值必须来自系统配置字典。
- 归口包全局共享，不按项目区分。
- 归口包优先按模块匹配，其次按子系统匹配。
- 归口包命名使用“模块测试归口包”或“系统测试归口包”。
- 归口包合并条目时按 `module + normalized title` 去重。
- 跨模块同名或相似测试条目保留，交由人工审核。

### 需求分析

- 本地分析和 AI 补充分析拆分为两个独立按钮。
- 本地分析先基于已发布测试条目、已发布归口包和已发布风险项推荐测试项。
- AI 补充分析在本地分析完成后由用户手动触发。
- AI 只补充本地未覆盖的测试项。
- 推荐项支持确认、排除、删除、纳入本地。
- AI 推荐项和人工新增推荐项都支持纳入本地，保存为本地测试条目草稿。
- 纳入本地只沉淀资产，不改变推荐项审核状态。
- 生成验证方案只使用已确认推荐项。
- 推荐项支持多选、全选、反选、批量删除、批量纳入本地、批量确认和批量排除。

### 验证方案导出

- 使用 `backend/templates/validation-plan-v1.docx` 作为 Word 底稿。
- 导出保留模板页眉页脚、样式、目录/域和静态结构。
- 动态替换验证背景、DUT 描述、参考文档、测试项目列表和测试项目详情。
- 测试项目详情固定输出 `3.x` 和 `3.x.1` 到 `3.x.7`。
- 测试工具、测试记录、需求符合性和 BUG 信息按表格导出。
- 测试记录表按模板合并环境温度、相对湿度、测试时间、测试地点、测试人员和测试结论等单元格。
- 文档来源测试项保留原始测试项块时，导出优先搬运原始块。
- AI 或手工来源测试项使用生成表格兜底。
- Word 目录保留可刷新的 TOC 域，真实页码依赖 Word 或 WPS 客户端刷新。

### 风险知识和反馈

- Jira、DFMEA 和风险资料沉淀为风险知识项。
- 风险项仅在发布后参与需求分析、本地检索和自由问答。
- 风险知识源支持单条发布、多选批量发布、单条删除和多选批量删除。
- 普通用户和管理员都可以提交 Bug 或新增需求反馈。
- 管理员可以回复反馈并更新状态。
- 反馈记录包含提交人、日期、类型、详细内容、管理员回复和状态。

### 自由应用

- 支持基于当前项目空间的连续对话。
- 可结合项目资料库和已配置大模型回答问题。
- 模型不可用时返回本地资料命中摘要。

## 当前部署和预览

当前预览地址：

```text
https://5173-aef0fcc0d31f5cd2.monkeycode-ai.online
```

当前预览服务：

- 前端 Vite：`5173`。
- 后端 Uvicorn：`8000`。
- 前端后台终端曾为：`term_1779105640964_115`。
- 后端后台终端曾为：`term_1779107930063_118`。

预览登录账号：

- 管理员：`admin / admin123`。
- 测试工程师：`tester / tester123`。

本地预览后端启动命令：

```bash
# 进入后端目录
cd /workspace/backend

# 启动后端服务
REPOSITORY_BACKEND=sqlalchemy STORAGE_BACKEND=local LOCAL_STORAGE_ROOT=/workspace/backend/storage python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

本地预览前端启动命令：

```bash
# 进入前端目录
cd /workspace/frontend

# 启动前端服务
npm run dev -- --host 0.0.0.0
```

注意：预览窗口适合临时调试，会话结束、容器重启或开发服务器停止后可能失效。

## 服务器部署建议

短期内网试用：

- 使用 `deploy/docker-compose.yml` 启动完整环境。
- 前端继续使用 Vite dev server。
- 用户访问 `http://<SERVER_IP>:5173`。
- 后端通过前端 `/api` 代理访问。

长期生产部署：

- 使用 `.env.production.example` 创建 `.env`。
- 替换数据库密码、MinIO 账号、模型网关和 `CORS_ORIGINS`。
- 前端执行 `npm run build` 生成 `frontend/dist`。
- 使用 Nginx 托管前端静态文件。
- Nginx 将 `/api/` 转发到后端 `127.0.0.1:8000`。
- PostgreSQL、Redis、MinIO 使用持久化卷或 bind mount。
- 定期备份 PostgreSQL、MinIO、`.env`、Nginx 配置和 Word 模板。

相关文档：

- `docs/server-deployment-guide.md`：迁移和内网试用部署。
- `docs/production-deployment-guide.md`：生产部署、Nginx、备份、升级和回滚。

## 测试和验证命令

后端测试：

```bash
# 进入后端目录
cd backend

# 运行测试
pytest
```

前端构建：

```bash
# 进入前端目录
cd frontend

# 构建前端
npm run build
```

最近完整验证记录：

- 后端测试曾通过：`141 passed`。
- 前端 `npm run build` 曾通过。
- 文档变更使用 `git diff --check` 校验过空白格式。

## Git 状态和近期提交

当前分支：`master`。

远程仓库：

```text
https://github.com/cquhanxiaodan/AI_test_sysytem.git
```

近期关键提交：

- `6c77acd docs: add production deployment guide`
- `03b99e9 docs: add server deployment guide`
- `da9441b fix: simplify document upload actions`
- `b16329f fix: support local folder document uploads`
- `f22ae2a fix: scope user settings per account`
- `94c1bd5 fix: show feedback reply dates`
- `ad9b30f fix: complete feedback and risk actions`
- `b50f948 feat: add feedback tracking module`
- `1936b12 fix: add select all for recommendations`
- `13a3d8c feat: add inverse selection batch actions`

当前未跟踪文件需要保留，交接时说明用途：

- `DNBSEQ-G99 ECR4.1康奈特RFID验证方案.docx`
- `export-258e538c-fd5e-418f-8f16-74fe213ffb8b/`
- `测试方案/`

这些文件未纳入当前代码提交，避免把用户资料或导出文件误提交到仓库。

## 关键业务决策

- 统一资料池是全局资产库，多项目通过标签、权限、适用范围和项目上下文复用资料。
- 项目空间代表某个产品项目的综合变更，例如 `G99 ECR4.0`。
- RFID 属于电子子系统下的模块，不作为一级子系统。
- 系统字典全局共享，仅管理员维护。
- AI 配置和统一资料池服务器导入目录按用户隔离。
- 资料发布后只生成测试条目或风险知识项。
- 测试条目发布后再自动形成或更新归口包。
- 需求分析本地推荐优先，AI 只补本地未覆盖项。
- 生成验证方案只使用已确认推荐项。
- Word 导出以模板底稿为准，保留目录、页眉页脚和样式。
- 生产部署建议前端静态化，由 Nginx 统一入口访问。

## 已知限制和注意事项

- 当前环境没有 LibreOffice 或 `soffice`，后端无法计算真实 Word 分页页码。
- Word 目录页码依赖 Word 或 WPS 客户端打开后刷新。
- 当前 `deploy/docker-compose.yml` 偏开发和内网试用，生产建议按 `docs/production-deployment-guide.md` 新增或维护 `docker-compose.prod.yml`。
- 当前本地预览 SQLite 中曾存在两个 RFID 历史归口包，需要业务确认后再做一次性数据清理。
- `python` 命令在当前环境不可用，使用 `python3`。
- 预览环境的 SQLite 数据和本地文件存储适合调试，长期使用应迁移到 PostgreSQL 和 MinIO。

## 后续推荐工作

1. 新增实际可运行的 `deploy/docker-compose.prod.yml`。
2. 新增生产版前端 Dockerfile 或 Nginx 镜像方案。
3. 补充从 SQLite + 本地文件存储迁移到 PostgreSQL + MinIO 的一次性脚本。
4. 确认当前预览库中 RFID 历史归口包的保留策略并清理重复包。
5. 为默认账号密码、用户管理和企业认证补生产加固方案。
6. 为 PostgreSQL 和 MinIO 增加自动备份脚本。
7. 在真实服务器上按 `docs/production-deployment-guide.md` 做一次部署演练。

## 接手建议

接手人员先阅读以下文档：

- `README.md`
- `docs/user-guide.md`
- `docs/server-deployment-guide.md`
- `docs/production-deployment-guide.md`
- `.monkeycode/MEMORY.md`

接手后的第一步建议：

```bash
# 查看仓库状态
git status --short

# 查看近期提交
git log -10 --oneline

# 运行后端测试
cd backend
pytest

# 构建前端
cd ../frontend
npm run build
```
