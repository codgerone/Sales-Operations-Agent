"""测试基础设施。

- 测试只连库名以 `_test` 结尾的库，绝不碰开发库。
- 连不上数据库时整轮测试以清楚的消息终止，不跳过（跳过会让"全部通过"失去意义）。
- 每个数据测试在一个外层事务中运行，Session 以保存点方式加入，测试结束整体回滚。
"""

import pytest
from alembic import command
from pydantic import ValidationError
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from sales_ops.config import TEST_DATABASE_SUFFIX, Settings, mask_url, resolve_test_database_url
from sales_ops.db import CONNECT_TIMEOUT_SECONDS, alembic_config, create_engine_from

MIGRATIONS_DATABASE_SUFFIX = "_migrations_test"


def require_test_database(url: str) -> None:
    name = make_url(url).database or ""
    if not name.endswith(TEST_DATABASE_SUFFIX):
        pytest.exit(
            f"拒绝运行：测试库名必须以 {TEST_DATABASE_SUFFIX} 结尾，当前为 {name!r}（{mask_url(url)}）",
            returncode=4,
        )


def _admin_engine(url: str) -> Engine:
    """连到同一服务器的 postgres 维护库，用于建库、删库（这两条语句不能在事务中执行）。"""
    admin_url = make_url(url).set(database="postgres")
    return create_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )


def ensure_database(url: str, *, recreate: bool = False) -> None:
    """测试库不存在时创建；recreate=True 时先删除再建，得到一个空库。"""
    require_test_database(url)
    name = make_url(url).database
    engine = _admin_engine(url)
    try:
        with engine.connect() as conn:
            quoted = conn.dialect.identifier_preparer.quote(name)
            if recreate:
                conn.execute(text(f"DROP DATABASE IF EXISTS {quoted} WITH (FORCE)"))
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            ).scalar()
            if not exists:
                conn.execute(text(f"CREATE DATABASE {quoted}"))
    except OperationalError as exc:
        pytest.exit(
            f"连不上测试数据库 {mask_url(url)}：{exc.orig}\n"
            "请先启动数据库容器：docker compose up -d",
            returncode=3,
        )
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    try:
        settings = Settings()
    except ValidationError:
        pytest.exit("缺少配置 DATABASE_URL：复制 .env.example 为 .env", returncode=4)
    url = resolve_test_database_url(settings)
    require_test_database(url)
    return url


@pytest.fixture
def empty_migrations_database(test_database_url: str) -> str:
    """迁移往返测试用的独立空库 <库名>_migrations_test：不存在时创建，存在时删除重建。"""
    url = make_url(test_database_url)
    base = url.database.removesuffix(TEST_DATABASE_SUFFIX)
    migrations_url = url.set(database=f"{base}{MIGRATIONS_DATABASE_SUFFIX}").render_as_string(
        hide_password=False
    )
    ensure_database(migrations_url, recreate=True)
    return migrations_url


@pytest.fixture(scope="session")
def engine(test_database_url: str):
    """测试库：不存在时创建，并迁移到最新。"""
    ensure_database(test_database_url)
    command.upgrade(alembic_config(test_database_url), "head")
    engine = create_engine_from(test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine):
    """一个测试一个 Session；被测代码里的 commit 只释放保存点，测试结束时外层事务回滚。"""
    with engine.connect() as connection:
        outer = connection.begin()
        s = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield s
        finally:
            s.close()
            outer.rollback()
