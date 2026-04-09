from pathlib import Path


def test_alembic_bootstrap_files_exist() -> None:
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
    assert Path("alembic/versions").exists()


def test_initial_revision_file_exists() -> None:
    revision_files = list(Path("alembic/versions").glob("*.py"))

    assert len(revision_files) == 1


def test_initial_revision_creates_core_tables_and_postgis() -> None:
    revision_files = list(Path("alembic/versions").glob("*.py"))
    revision_text = (
        revision_files[0].read_text(encoding="utf-8") if revision_files else ""
    )

    assert "CREATE EXTENSION IF NOT EXISTS postgis" in revision_text
    assert "op.create_table(" in revision_text
    assert '"projects"' in revision_text
    assert '"import_batches"' in revision_text
    assert '"obstacles"' in revision_text
