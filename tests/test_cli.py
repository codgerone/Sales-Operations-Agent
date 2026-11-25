import pytest

from sales_ops import cli
from sales_ops.config import Settings


@pytest.fixture
def use_database(monkeypatch):
    """让 check 读到指定的 DATABASE_URL，且不读项目的 .env。"""

    def _use(url: str | None) -> None:
        if url is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", url)
        monkeypatch.setattr(cli, "Settings", lambda: Settings(_env_file=None))

    return _use


def test_check_ok(engine, test_database_url, use_database, capsys):
    use_database(test_database_url)
    assert cli.main(["check"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "（最新）" in out
    assert "sales_ops_dev" not in out  # 密码已遮蔽


def test_check_migration_not_applied(empty_migrations_database, use_database, capsys):
    use_database(empty_migrations_database)
    assert cli.main(["check"]) == cli.EXIT_MIGRATION
    assert "未执行任何迁移" in capsys.readouterr().out


def test_check_config_missing(use_database, capsys):
    use_database(None)
    assert cli.main(["check"]) == cli.EXIT_CONFIG
    assert "DATABASE_URL" in capsys.readouterr().out


def test_check_database_unreachable(use_database, capsys):
    # 端口 1 上没有服务，连接被立即拒绝。
    use_database("postgresql+psycopg://u:secret@127.0.0.1:1/nothing")
    assert cli.main(["check"]) == cli.EXIT_DB_UNREACHABLE
    out = capsys.readouterr().out
    assert "失败" in out and "secret" not in out
