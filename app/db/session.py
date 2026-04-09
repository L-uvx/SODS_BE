from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings


settings = Settings.from_env()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
