from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


# 提供请求级数据库会话依赖。
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
