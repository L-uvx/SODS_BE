from importlib import reload

from sqlalchemy.orm import DeclarativeBase

from app.db.base import Base
from app.db.session import SessionLocal, engine


def test_base_is_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_engine_uses_configured_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///./tmp.db")

    import app.db.session as session_module

    reload(session_module)

    assert str(session_module.engine.url) == "sqlite+pysqlite:///./tmp.db"


def test_session_factory_binds_to_engine() -> None:
    assert SessionLocal.kw["bind"] is engine
