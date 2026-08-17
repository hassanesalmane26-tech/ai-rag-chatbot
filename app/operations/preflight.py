"""Non-mutating release/runtime preflight suitable for CI and operators."""

import json
from pathlib import Path

from sqlalchemy import inspect, text

from app.core.config import settings
from app.database.database import engine
from app.database.schema import HEAD_REVISION, verify_genesis_schema


def report() -> dict:
    verification = verify_genesis_schema(engine)
    revision = None
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        if inspect(engine).has_table("alembic_version"):
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar_one_or_none()
    frontend_artifact = Path("frontend/dist/index.html")
    return {
        "database": "ok",
        "schema_compatible": verification.compatible,
        "schema_issues": list(verification.issues),
        "migration_revision": revision,
        "migration_head": HEAD_REVISION,
        "migration_current": revision == HEAD_REVISION,
        "original_storage_present": settings.documents_path.is_dir(),
        "vector_storage_present": settings.vector_db_path.is_dir(),
        "frontend_artifact_present": frontend_artifact.is_file(),
    }


def main() -> None:
    result = report()
    print(json.dumps(result, sort_keys=True))
    if not all(
        result[key]
        for key in (
            "schema_compatible",
            "migration_current",
            "original_storage_present",
            "vector_storage_present",
            "frontend_artifact_present",
        )
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
