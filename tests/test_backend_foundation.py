import asyncio
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'trident_genesis_tests.sqlite'}"
)
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from alembic import command
from alembic.config import Config
import httpx
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.core.errors import BusinessRuleError, ConflictError
from app.database.database import Base
from app.database import genesis_models, models  # noqa: F401
from app.database.schema import (
    BASELINE_REVISION,
    EXPECTED_COLUMNS,
    HEAD_REVISION,
    verify_genesis_schema,
)
from app.main import create_app


async def get_from_application(application, *paths):
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return [await client.get(path) for path in paths]


class SettingsTests(unittest.TestCase):
    def test_legacy_and_canonical_environment_names_are_compatible(self):
        legacy = Settings(DATABASE_URL="sqlite://", OPENAI_API_KEY="legacy", DEBUG="true", _env_file=None)
        canonical = Settings(
            TRIDENT_DATABASE_URL="sqlite://",
            TRIDENT_OPENAI_API_KEY="canonical",
            TRIDENT_ENV="test",
            _env_file=None,
        )
        self.assertTrue(legacy.debug)
        self.assertEqual(legacy.openai_key(), "legacy")
        self.assertEqual(canonical.environment, "test")
        self.assertEqual(canonical.openai_key(), "canonical")

    def test_production_rejects_debug_and_missing_database(self):
        with self.assertRaises(ValueError):
            Settings(TRIDENT_ENV="production", TRIDENT_DATABASE_URL="sqlite://", TRIDENT_DEBUG=True, _env_file=None)
        with self.assertRaises(ValueError):
            Settings(TRIDENT_DATABASE_URL="", _env_file=None)

    def test_secret_is_redacted(self):
        configured = Settings(TRIDENT_DATABASE_URL="sqlite://", TRIDENT_OPENAI_API_KEY="secret-value", _env_file=None)
        self.assertNotIn("secret-value", repr(configured))


class MigrationFoundationTests(unittest.TestCase):
    def alembic_config(self, database_url: str) -> Config:
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", database_url)
        return config

    def test_baseline_upgrades_an_empty_database(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database_url = f"sqlite:///{Path(tempdir) / 'empty.sqlite'}"
            command.upgrade(self.alembic_config(database_url), "head")
            engine = create_engine(database_url)
            try:
                self.assertTrue(verify_genesis_schema(engine).compatible)
                with engine.connect() as connection:
                    revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                self.assertEqual(revision, HEAD_REVISION)
            finally:
                engine.dispose()


class ApplicationFoundationTests(unittest.TestCase):
    def test_lifecycle_does_not_create_schema(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database_url = f"sqlite:///{Path(tempdir) / 'lifecycle.sqlite'}"
            database_engine = create_engine(database_url)
            configured = Settings(TRIDENT_ENV="test", TRIDENT_DATABASE_URL=database_url, _env_file=None)
            application = create_app(configured, database_engine)
            [response] = asyncio.run(get_from_application(application, "/health/live"))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(inspect(database_engine).get_table_names(), [])

    def test_structured_business_conflict_and_internal_errors(self):
        database_engine = create_engine("sqlite://")
        configured = Settings(TRIDENT_ENV="test", TRIDENT_DATABASE_URL="sqlite://", _env_file=None)
        application = create_app(configured, database_engine)

        @application.get("/_test/conflict")
        def conflict():
            raise ConflictError()

        @application.get("/_test/business")
        def business():
            raise BusinessRuleError("Règle métier refusée.")

        @application.get("/_test/internal")
        def internal():
            raise RuntimeError("private internal detail")

        conflict_response, business_response, internal_response = asyncio.run(
            get_from_application(application, "/_test/conflict", "/_test/business", "/_test/internal")
        )
        self.assertEqual(conflict_response.status_code, 409)
        self.assertEqual(conflict_response.json()["error"]["code"], "RESOURCE_CONFLICT")
        self.assertEqual(business_response.status_code, 422)
        self.assertEqual(business_response.json()["error"]["code"], "BUSINESS_RULE_VIOLATION")
        self.assertEqual(internal_response.status_code, 500)
        self.assertEqual(internal_response.json()["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("private internal detail", internal_response.text)

class MigrationAdoptionTests(unittest.TestCase):
    def alembic_config(self, database_url: str) -> Config:
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", database_url)
        return config

    def test_existing_schema_is_verified_then_stamped_without_product_ddl(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database_url = f"sqlite:///{Path(tempdir) / 'existing.sqlite'}"
            engine = create_engine(database_url)
            command.upgrade(self.alembic_config(database_url), BASELINE_REVISION)
            with engine.begin() as connection:
                connection.execute(text("DROP TABLE alembic_version"))
            before = set(inspect(engine).get_table_names())
            verification = verify_genesis_schema(engine, BASELINE_REVISION)
            self.assertTrue(verification.compatible, verification.issues)
            engine.dispose()

            command.stamp(self.alembic_config(database_url), BASELINE_REVISION)
            command.upgrade(self.alembic_config(database_url), "head")
            checked = create_engine(database_url)
            try:
                after = set(inspect(checked).get_table_names())
                self.assertEqual(after - {"alembic_version"}, before)
                for table, columns in EXPECTED_COLUMNS.items():
                    self.assertTrue(columns.issubset({item["name"] for item in inspect(checked).get_columns(table)}))
                self.assertTrue(verify_genesis_schema(checked).compatible)
            finally:
                checked.dispose()

    def test_schema_verifier_reports_an_incomplete_database(self):
        with tempfile.TemporaryDirectory() as tempdir:
            engine = create_engine(f"sqlite:///{Path(tempdir) / 'incomplete.sqlite'}")
            try:
                result = verify_genesis_schema(engine)
                self.assertFalse(result.compatible)
                self.assertIn("missing table: workspaces", result.issues)
            finally:
                engine.dispose()
