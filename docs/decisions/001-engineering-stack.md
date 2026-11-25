# 001 工程技术栈

日期：2026-11-25（V1.1）
状态：有效

## 背景

V1.1 建立之后所有版本共用的工程骨架，需要确定 Python 版本、依赖管理、数据库、本机数据库的运行方式、ORM 与迁移工具。约束：

- 将复用 Minimal-RAG（要求 Python `>=3.11,<3.12`，用 uv）；接入方式（进程内的库，或 MCP / HTTP 服务）在 V3.1 决定。
- 业务数据含金额（定点小数）与跨时区的时刻；V1.4 有并发修改，V6.1 有后台 Worker；迁移失败要能整体回滚。
- 数据库模型、API 模型（V1.3）与提取模型（V3.2）分开定义。
- V10.4 部署使用 Docker。

## 决定

| 问题 | 选项 | 结论 | 理由 |
|---|---|---|---|
| Python 版本 | 3.11；3.12 / 3.13 | **3.11** | 两种接入 Minimal-RAG 的方式都保留；选更高版本等于在 V3.1 前排除库方式 |
| 依赖管理 | uv；Poetry；pip + venv + requirements.txt | **uv** | 跨平台锁文件；固定 Python 版本；可用本地路径或 git 标签依赖 Minimal-RAG；与 Minimal-RAG 一套工具。pip 方案没有可靠的锁文件；Poetry 需另装且不管 Python 版本 |
| 数据库 | PostgreSQL；SQLite；MySQL | **PostgreSQL** | 原生定点小数与 `timestamptz`；多写者并发；DDL 在事务中，迁移可整体回滚。SQLite 只能单写者、无原生定点小数；MySQL 的 DDL 不在事务中、无 `timestamptz`。开发、测试、部署用同一种数据库 |
| 本机运行 PostgreSQL | Docker Desktop + Compose；Windows 安装包装成系统服务 | **Docker Desktop + Compose** | 版本、端口、账号写在仓库的 `compose.yaml`，一条命令启停与重建；系统中不多常驻服务；与部署方式一致。代价：需先装 WSL 2，Docker Desktop 常驻占用内存 |
| ORM 与迁移 | SQLAlchemy 2.0 + Alembic；SQLModel + Alembic；原生 SQL + 手写 SQL 迁移 | **SQLAlchemy 2.0 + Alembic** | 对事务、锁、关系控制最细；数据库模型与其他模型分开。SQLModel 把表模型与接口模型合成一个类，与模型分开的要求相反；手写 SQL 迁移使模型与迁移两份描述需人工保持一致 |

## 影响

- 进程内接入 Minimal-RAG 时，依赖兼容性由 uv 在锁定时检查。
- 测试必须连接运行中的 PostgreSQL（`design.md` 第 8 节）。
