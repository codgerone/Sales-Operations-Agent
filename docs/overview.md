# 系统概览

最后更新：2026-11-25（V1.1 工程骨架）

本文写系统现在能做什么、怎么准备环境与运行、怎么验收。架构与约定见 `design.md`。

## 1. 现在能做什么

- 工程骨架：配置、本机数据库、数据库访问、迁移、测试与命令行检查。
- 一张业务表 `customer`（`id`、`name`、`created_at`）。实体与字段的正式设计在 V1.2。
- 没有 API、界面与 LLM 调用。

## 2. 准备环境

前提：uv；Docker Desktop（已启动）。

| 步骤 | 命令 |
|---|---|
| 启动本机数据库 | `docker compose up -d`（`docker compose ps` 中 `db` 为 healthy） |
| 配置 | 复制 `.env.example` 为 `.env` |
| 安装依赖与 Python 3.11 | `uv sync` |
| 建表 | `uv run alembic upgrade head` |
| 检查 | `uv run sales-ops check` |

- 数据库地址的主机写 `127.0.0.1`，不写 `localhost`：本机 `localhost` 先解析为 IPv6 `::1`，连接挂起直到超时。
- 数据库容器的账号与密码只用于本机，写在 `compose.yaml` 与 `.env.example` 中。
- 数据保存在命名数据卷中；`docker compose down -v` 删除数据卷，即清空数据库。

## 3. 常用命令

| 命令 | 作用 |
|---|---|
| `uv run sales-ops check` | 检查配置、数据库连接与迁移版本 |
| `uv run alembic upgrade head` / `downgrade base` | 迁移到最新 / 撤销全部迁移 |
| `uv run alembic current` / `history` | 当前迁移版本 / 迁移链 |
| `uv run alembic revision --autogenerate -m "<说明>"` | 由模型与数据库的差异生成迁移草稿（须人工审核） |
| `uv run pytest` | 运行测试（需要数据库容器在运行） |
| `uv run ruff check` / `ruff format` | 代码检查 / 格式化 |
| `docker compose stop db` / `start db` | 停止 / 启动数据库 |
| `docker compose exec db psql -U sales_ops` | 进入数据库命令行 |

`sales-ops check` 的退出码：

| 退出码 | 含义 |
|---|---|
| 0 | 全部正常 |
| 1 | 配置缺失或无效 |
| 2 | 连不上数据库 |
| 3 | 迁移未执行或不是最新 |

## 4. 写入与读取

在 `uv run python` 中粘贴（数据库已迁移到最新）：

```python
from sqlalchemy import select
from sales_ops.config import Settings
from sales_ops.db import create_engine_from, make_session_factory
from sales_ops.business.models import Customer
factory = make_session_factory(create_engine_from(Settings().database_url.get_secret_value()))
with factory() as s, s.begin(): s.add(Customer(name="Acme Instruments GmbH"))

with factory() as s: print([(c.id, c.name, c.created_at) for c in s.scalars(select(Customer))])

```

第一个 `with` 写入并提交；第二个 `with` 用新的 Session 查询并打印。`id` 与 `created_at` 由数据库生成。

## 5. 验收

- 自动检查：`uv run pytest`、`uv run ruff check`、`uv run ruff format --check` 全部通过。
- 测试使用单独的测试库（`<库名>_test`，迁移往返测试另用 `<库名>_migrations_test`），不影响开发库；库不存在时自动创建。
