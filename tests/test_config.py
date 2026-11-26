import pytest
from pydantic import ValidationError

from sales_ops.config import Settings, mask_url, resolve_test_database_url

URL = "postgresql+psycopg://u:secret@localhost:5432/sales_ops"


def test_missing_database_url_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "database_url" in str(exc.value)


def test_env_var_overrides_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql+psycopg://u:p@from-file/db\n", encoding="utf-8")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert "from-file" in Settings(_env_file=env_file).database_url.get_secret_value()

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@from-env/db")
    assert "from-env" in Settings(_env_file=env_file).database_url.get_secret_value()


def test_secret_is_hidden_in_str_and_repr(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    settings = Settings(_env_file=None)
    assert "secret" not in str(settings.database_url)
    assert "secret" not in repr(settings)


def test_mask_url_hides_password():
    assert mask_url(URL) == "postgresql+psycopg://u:***@localhost:5432/sales_ops"


def test_test_database_url_derived_from_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    settings = Settings(_env_file=None)
    assert (
        resolve_test_database_url(settings, environ={})
        == "postgresql+psycopg://u:secret@localhost:5432/sales_ops_test"
    )


def test_test_database_url_explicit_wins(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", URL)
    settings = Settings(_env_file=None)
    explicit = "postgresql+psycopg://u:p@other:5432/x_test"
    assert resolve_test_database_url(settings, environ={"TEST_DATABASE_URL": explicit}) == explicit
