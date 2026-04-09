from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so metadata is populated for Alembic and tests.
from app.models.import_batch import ImportBatch  # noqa: E402,F401
from app.models.obstacle import Obstacle  # noqa: E402,F401
from app.models.project import Project  # noqa: E402,F401
