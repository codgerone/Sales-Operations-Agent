from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from sales_ops.business import models  # noqa: F401  注册模型到 Base.metadata
from sales_ops.db import Base, alembic_config, create_engine_from


def _tables(url: str) -> set[str]:
    engine = create_engine_from(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade(empty_migrations_database):
    """在空库上 upgrade head → downgrade base → upgrade head，每个迁移的升降都能执行。"""
    url = empty_migrations_database
    cfg = alembic_config(url)

    command.upgrade(cfg, "head")
    assert "customer" in _tables(url)

    command.downgrade(cfg, "base")
    assert _tables(url) == {"alembic_version"}

    command.upgrade(cfg, "head")
    assert "customer" in _tables(url)


def test_models_match_latest_migration(engine):
    """迁移到最新的库与模型比较无差异：改了模型就必须有对应迁移。"""
    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)
    assert diff == []
