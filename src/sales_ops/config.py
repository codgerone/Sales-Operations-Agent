"""配置：从环境变量与项目根目录的 .env 读取，环境变量优先。"""

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"
TEST_DATABASE_SUFFIX = "_test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: SecretStr


def mask_url(url: str) -> str:
    """数据库地址的可显示形式：密码替换为 ***。"""
    return make_url(url).render_as_string(hide_password=True)


def resolve_test_database_url(settings: Settings, environ: Mapping[str, str] = os.environ) -> str:
    """测试库地址：TEST_DATABASE_URL；未设置时把 database_url 的库名改为 <库名>_test。"""
    explicit = environ.get(TEST_DATABASE_URL_ENV)
    if explicit:
        return explicit
    url = make_url(settings.database_url.get_secret_value())
    return url.set(database=f"{url.database}{TEST_DATABASE_SUFFIX}").render_as_string(
        hide_password=False
    )
