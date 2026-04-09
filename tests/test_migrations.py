from pathlib import Path


def test_alembic_bootstrap_files_exist() -> None:
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
    assert Path("alembic/versions").exists()
