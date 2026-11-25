"""命令行入口：`sales-ops check` 检查运行环境。

退出码区分失败类型，供脚本判断；输出供人阅读。
"""

import argparse
import platform

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import ArgumentError, OperationalError

from sales_ops.config import Settings, mask_url
from sales_ops.db import alembic_config, create_engine_from

EXIT_OK = 0
EXIT_CONFIG = 1
EXIT_DB_UNREACHABLE = 2
EXIT_MIGRATION = 3

CONFIG_HINT = "复制 .env.example 为 .env，或设置环境变量 DATABASE_URL"


def _line(label: str, value: str) -> None:
    print(f"{label}：{value}")


def check() -> int:
    _line("Python 版本", platform.python_version())

    try:
        settings = Settings()
    except ValidationError as exc:
        names = ", ".join(str(err["loc"][0]).upper() for err in exc.errors())
        _line("配置", f"缺失或无效：{names}。{CONFIG_HINT}")
        return EXIT_CONFIG

    url = settings.database_url.get_secret_value()
    try:
        masked = mask_url(url)
        engine = create_engine_from(url)
    except ArgumentError as exc:
        _line("配置", f"DATABASE_URL 无效：{exc}。{CONFIG_HINT}")
        return EXIT_CONFIG
    _line("数据库地址", masked)

    try:
        with engine.connect() as conn:
            server_version = conn.execute(text("SHOW server_version")).scalar()
            current = set(MigrationContext.configure(conn).get_current_heads())
    except OperationalError as exc:
        _line("数据库连接", f"失败：{str(exc.orig).strip()}")
        return EXIT_DB_UNREACHABLE
    finally:
        engine.dispose()
    _line("数据库连接", f"正常（PostgreSQL {server_version}）")

    latest = set(ScriptDirectory.from_config(alembic_config(url)).get_heads())
    if current != latest:
        _line(
            "迁移版本",
            f"不是最新（当前 {', '.join(sorted(current)) or '未执行任何迁移'}，"
            f"最新 {', '.join(sorted(latest))}）。执行 uv run alembic upgrade head",
        )
        return EXIT_MIGRATION
    _line("迁移版本", f"{', '.join(sorted(current))}（最新）")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sales-ops", description="Sales Operations Agent")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="检查配置、数据库连接与迁移版本")
    args = parser.parse_args(argv)

    if args.command == "check":
        return check()
    parser.error(f"未知命令：{args.command}")
    return EXIT_CONFIG
