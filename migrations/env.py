"""Alembic 运行环境。

数据库地址的来源（按优先级）：
1. 调用方放入 `config.attributes["database_url"]`（测试与 `sales-ops check` 用它指向指定的库）；
2. `Settings().database_url`（.env / 环境变量）。
"""

from logging.config import fileConfig

from alembic import context

from sales_ops.business import models  # noqa: F401  注册模型到 Base.metadata
from sales_ops.config import Settings
from sales_ops.db import Base, create_engine_from

config = context.config
if config.config_file_name is not None and not config.attributes.get("skip_logging_config"):
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def database_url() -> str:
    url = config.attributes.get("database_url")
    if url:
        return url
    return Settings().database_url.get_secret_value()


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine_from(database_url())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
