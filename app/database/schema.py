"""Read-only verification required before adopting an existing database."""

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database.database import Base
from app.database import genesis_models, models  # noqa: F401 - register metadata

BASELINE_REVISION = "0001_genesis_baseline"
HEAD_REVISION = "0003_workspace_memory"
CURRENT_COLUMNS = {
    table.name: {column.name for column in table.columns}
    for table in Base.metadata.sorted_tables
}
BASELINE_COLUMNS = {
    **{name: columns for name, columns in CURRENT_COLUMNS.items() if name != "workspace_memories"},
    "workspace_documents": CURRENT_COLUMNS["workspace_documents"]
    - {"content_hash", "version", "ingestion_attempts", "chunk_count", "updated_at"},
}
DURABLE_INGESTION_COLUMNS = {
    name: columns for name, columns in CURRENT_COLUMNS.items() if name != "workspace_memories"
}
EXPECTED_COLUMNS = CURRENT_COLUMNS


@dataclass(frozen=True)
class SchemaVerification:
    compatible: bool
    issues: tuple[str, ...]


def _type_signature(column_type) -> tuple[str, int | None]:
    affinity = getattr(column_type, "_type_affinity", type(column_type))
    return affinity.__name__, getattr(column_type, "length", None)


def verify_genesis_schema(
    engine: Engine, target_revision: str = HEAD_REVISION
) -> SchemaVerification:
    """Compare the mapped baseline without performing DDL or data writes."""
    if target_revision == BASELINE_REVISION:
        expected_columns = BASELINE_COLUMNS
    elif target_revision == "0002_durable_document_ingestion":
        expected_columns = DURABLE_INGESTION_COLUMNS
    else:
        expected_columns = CURRENT_COLUMNS
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    expected_tables = set(expected_columns)
    issues = []

    for table in sorted(expected_tables - actual_tables):
        issues.append(f"missing table: {table}")
    for table in sorted(actual_tables - expected_tables - {"alembic_version"}):
        issues.append(f"unexpected table: {table}")

    for table_name in sorted(expected_tables & actual_tables):
        mapped_table = Base.metadata.tables[table_name]
        actual_columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        missing = set(expected_columns[table_name]) - set(actual_columns)
        if missing:
            issues.append(f"{table_name} missing columns: {','.join(sorted(missing))}")
        extra = set(actual_columns) - set(expected_columns[table_name])
        if extra:
            issues.append(f"{table_name} unexpected columns: {','.join(sorted(extra))}")
        for mapped_column in mapped_table.columns:
            if mapped_column.name not in expected_columns[table_name]:
                continue
            actual = actual_columns.get(mapped_column.name)
            if not actual:
                continue
            if bool(actual["nullable"]) != bool(mapped_column.nullable):
                issues.append(f"{table_name}.{mapped_column.name} nullable mismatch")
            if _type_signature(actual["type"]) != _type_signature(mapped_column.type):
                issues.append(f"{table_name}.{mapped_column.name} type mismatch")

        actual_pk = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
        mapped_pk = {column.name for column in mapped_table.primary_key.columns}
        if actual_pk != mapped_pk:
            issues.append(f"{table_name} primary key mismatch")

        actual_fks = {
            (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
            for fk in inspector.get_foreign_keys(table_name)
        }
        mapped_fks = {
            ((column.name,), foreign_key.column.table.name, (foreign_key.column.name,))
            for column in mapped_table.columns
            for foreign_key in column.foreign_keys
        }
        if actual_fks != mapped_fks:
            issues.append(f"{table_name} foreign keys mismatch")

        actual_indexes = {
            (tuple(index["column_names"]), bool(index.get("unique")))
            for index in inspector.get_indexes(table_name)
            if not index.get("duplicates_constraint")
        }
        mapped_indexes = {
            (tuple(column.name for column in index.columns), bool(index.unique))
            for index in mapped_table.indexes
            if all(column.name in expected_columns[table_name] for column in index.columns)
        }
        if not mapped_indexes.issubset(actual_indexes):
            issues.append(f"{table_name} indexes mismatch")

        actual_uniques = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)
        }
        mapped_uniques = {
            tuple(column.name for column in constraint.columns)
            for constraint in mapped_table.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }
        if actual_uniques != mapped_uniques:
            issues.append(f"{table_name} unique constraints mismatch")

    return SchemaVerification(compatible=not issues, issues=tuple(issues))
