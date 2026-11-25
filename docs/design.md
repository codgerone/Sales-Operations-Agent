# 系统设计

最后更新：2026-11-25（V1.1 工程骨架）

本文写架构、数据模型、各模块职责与关键机制。只写已实现的部分；字段与接口细节以代码和测试为准。

## 1. 技术栈

| 环节 | 选择 | 决策 |
|---|---|---|
| 语言 | Python 3.11（`.python-version`；`requires-python >= 3.11`） | `decisions/001` |
| 依赖管理 | uv；`uv.lock` 进仓库 | `decisions/001` |
| 数据库 | PostgreSQL 18；本机由 Docker Compose 运行 | `decisions/001` |
| 数据库访问 | SQLAlchemy 2.x ORM（同步），驱动 psycopg 3 | `decisions/001` |
| 迁移 | Alembic | `decisions/001` |
| 配置 | pydantic-settings | — |
| 测试与检查 | pytest；Ruff（检查规则：默认 + `I`、`UP`、`B`；格式化） | — |

## 2. 目录与模块

- src 布局：代码在 `src/sales_ops/`，以可编辑方式安装进 `.venv`；测试只能通过已安装的包导入代码。
- 模块化单体：每个后台能力模块是 `sales_ops` 下的一个子包（`vision.md` 第 4 节）。已有：`business`（业务数据）。
- 横向基础设施在包的顶层：`config.py`（配置）、`db.py`（数据库访问）、`cli.py`（命令行）。

| 文件 | 职责 |
|---|---|
| `config.py` | `Settings`；数据库地址的密码遮蔽；测试库地址推导 |
| `db.py` | Engine 与 Session 工厂；ORM 基类与约束命名约定；指向给定库的 Alembic 配置 |
| `business/models.py` | 业务数据的数据库模型 |
| `cli.py` | 入口命令 `sales-ops` |
| `migrations/` | Alembic 运行环境与迁移文件 |

## 3. 配置

- 来源：环境变量与项目根目录的 `.env`，环境变量优先。`.env` 不进 git，`.env.example` 列出全部配置项。
- 必填项缺失或无效时，构造 `Settings` 即失败。
- 密钥类配置用 `SecretStr`，字符串形式与 `repr` 不含明文；对外显示数据库地址时密码替换为 `***`。
- 测试库地址：环境变量 `TEST_DATABASE_URL`；未设置时为 `DATABASE_URL` 的库名加后缀 `_test`。

## 4. 数据库访问

- 模块导入时不连接数据库、不读配置；调用方传入地址创建 Engine（`create_engine_from`），再创建 Session 工厂（`make_session_factory`）。
- Engine：连接前检测（`pool_pre_ping`）；连接超时 5 秒。
- 会话：一次操作一个 Session，事务由 `with factory() as s, s.begin():` 包住，正常退出提交、异常回滚。提交后对象属性不过期（`expire_on_commit=False`），Session 关闭后仍可读取已加载的值。
- 约束命名约定（`Base.metadata`）：主键 `pk_<表>`；外键 `fk_<表>_<列>_<被引用表>`；唯一 `uq_<表>_<列…>`；检查 `ck_<表>_<名>`；索引 `ix_<列…>`。

## 5. 数据模型

| 表 | 列 | 约束 |
|---|---|---|
| `customer` | `id` BIGINT IDENTITY（ALWAYS）；`name` TEXT；`created_at` TIMESTAMPTZ，默认 `now()` | 主键 `pk_customer`；三列非空 |

## 6. 迁移

- 数据库结构只通过 Alembic 迁移改变，不用 `create_all`。
- 数据库地址：调用方放入 `config.attributes["database_url"]` 时用它（测试与命令行），否则取 `Settings().database_url`。`alembic.ini` 不写地址，且只含 ASCII 字符（Alembic 按系统区域编码读取它）。
- 自动生成开启类型比较；生成后经 Ruff 修正导入顺序并格式化。自动生成的迁移是草稿，须人工审核（改名、CHECK 约束、数据迁移不能自动识别）。
- 文件名：`<日期>_<编号>_<说明>.py`（日期为 UTC）。
- 已提交的迁移不再修改；改模型与对应迁移在同一个提交中；每个迁移写 `downgrade`。

## 7. 命令行

- `sales-ops check` 依次检查配置、数据库连接与服务器版本、迁移版本（数据库当前版本与迁移链最新版本是否一致），在第一个失败处停止。退出码见 `overview.md` 第 3 节。

## 8. 测试

- 测试连接真实的 PostgreSQL，不用 SQLite 或模拟对象代替。
- 测试库守卫：库名不以 `_test` 结尾时整轮测试终止。
- 数据库连不上或缺少配置时，整轮测试以说明原因的消息终止，不跳过。
- 会话级：测试库不存在时创建，并迁移到最新。
- 函数级 `session`：每个测试在一个外层事务中运行，Session 以保存点方式加入（被测代码的 `commit` 只释放保存点），测试结束时外层事务回滚。
- 迁移测试：在每次重建的空库 `<库名>_migrations_test` 上执行 `upgrade head → downgrade base → upgrade head`；在测试库上比较模型与最新迁移，要求无差异。
