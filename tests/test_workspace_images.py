"""No network/provider credentials: real API, temporary DB/storage, deterministic provider."""
import asyncio
import base64
import io
import os
import tempfile
import unittest
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.database.database import Base, get_db
from app.database.genesis_models import Workspace, Conversation, WorkspaceMessage
from app.identity.models import User, ExternalIdentity
from app.identity.contracts import VerifiedExternalIdentity, InvalidIdentityCredential
from app.tenancy.models import Organization, Membership
from app.images.models import ImageArtifact
from app.images.contracts import ImageGenerationResult, ImageGenerationRequest, normalize_image, image_intent, image_edit_intent, MAX_IMAGE_BYTES
from app.images.provider import OpenAIImageProvider, configured_provider
from app.images.service import process_image, image_storage, reconcile_images
from app.main import create_app
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text


def png():
    output = io.BytesIO()
    Image.new("RGB", (24, 16), "navy").save(output, format="PNG")
    return output.getvalue()


class TestVerifier:
    async def verify(self, credential):
        if credential not in {"owner", "other", "collaborator"}:
            raise InvalidIdentityCredential("invalid")
        return VerifiedExternalIdentity("https://images.test", credential)


class WorkspaceImagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{self.temp.name}/test.sqlite", connect_args={"check_same_thread": False})
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        self.config = Settings(database_url=str(self.engine.url), environment="test", security_mode="oidc",
            oidc_issuer="https://images.test", oidc_audience="images", openai_api_key="test-only",
            image_provider="openai", images_path=Path(self.temp.name) / "images")
        self.app = create_app(self.config, self.engine, TestVerifier())
        def database():
            with self.factory() as db: yield db
        self.app.dependency_overrides[get_db] = database
        with self.factory() as db:
            org = Organization(id="org", name="Test", slug="test", ownership_state="active")
            foreign = Organization(id="foreign", name="Other", slug="other", ownership_state="active")
            db.add_all([org, foreign]); db.flush()
            for subject, organization in [("owner", "org"), ("other", "foreign"), ("collaborator", "org")]:
                db.add(User(id=subject, display_name=subject)); db.flush()
                db.add_all([ExternalIdentity(user_id=subject, issuer="https://images.test", subject=subject),
                    Membership(user_id=subject, organization_id=organization, role="owner")])
            db.add_all([Workspace(id="ws", name="Images", organization_id="org"), Workspace(id="ws2", name="Separate", organization_id="org"), Workspace(id="secret", name="Private", organization_id="foreign")]); db.flush()
            db.add_all([Conversation(id="conv", workspace_id="ws"), Conversation(id="conv2", workspace_id="ws2")]); db.commit()
        self.provider = Mock()
        self.provider.generate.return_value = ImageGenerationResult(png(), "test", "test-model")

    def tearDown(self):
        self.engine.dispose(); self.temp.cleanup()

    def request(self, method, path, token="owner", **kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test") as client:
                return await client.request(method, path, headers={"Authorization": f"Bearer {token}"} if token else {}, **kwargs)
        return asyncio.run(run())

    def enqueue(self, key="request-1", **options):
        payload = {"prompt": "Une ville céleste", "request_key": key, "aspect_ratio": "3:2", **options}
        return self.request("POST", "/v1/workspaces/ws/conversations/conv/images", data=payload)

    def process(self, identifier):
        with self.factory() as db: return process_image(db, identifier, self.provider, image_storage(self.config))

    def test_generation_persistence_metadata_content_and_idempotence(self):
        response = self.enqueue(); self.assertEqual(response.status_code, 202, response.text)
        item = response.json()["data"]
        self.assertEqual(item["status"], "queued")
        self.assertEqual(self.enqueue().json()["data"]["id"], item["id"])
        self.assertEqual(self.enqueue(prompt="Different").status_code, 409)
        self.assertTrue(self.process(item["id"]))
        self.assertFalse(self.process(item["id"]))
        self.assertEqual(self.provider.generate.call_count, 1)
        result = self.request("GET", "/v1/workspaces/ws/images").json()["data"][0]
        self.assertEqual(result["status"], "completed")
        self.assertEqual((result["width"], result["height"]), (24, 16))
        self.assertEqual(result["conversation_id"], "conv")
        self.assertNotIn("provider", result); self.assertNotIn("source_key", result)
        content = self.request("GET", f"/v1/workspaces/ws/images/{item['id']}/content")
        self.assertEqual(content.status_code, 200); self.assertEqual(content.headers["content-type"], "image/png")
        self.assertIn("no-store", content.headers["cache-control"])
        with self.factory() as db:
            self.assertEqual(db.query(WorkspaceMessage).count(), 2)
            self.assertEqual(db.get(ImageArtifact, item["id"]).provider, "test")

    def test_missing_config_does_not_create_false_task_or_message(self):
        self.config.image_provider = "disabled"
        self.assertFalse(self.request("GET", "/v1/workspaces/ws/images/capability").json()["data"]["available"])
        self.assertEqual(self.enqueue().status_code, 503)
        with self.factory() as db: self.assertEqual(db.query(WorkspaceMessage).count(), 0)
        self.assertIsNone(configured_provider(self.config))

    def test_auth_workspace_and_conversation_boundaries(self):
        self.assertEqual(self.request("GET", "/v1/workspaces/ws/images", token=None).status_code, 401)
        for path in ("/images", "/images/capability"):
            self.assertEqual(self.request("GET", "/v1/workspaces/ws" + path, token="other").status_code, 403)
        response = self.request("POST", "/v1/workspaces/ws/conversations/conv2/images", data={"prompt": "image", "request_key": "r"})
        self.assertEqual(response.status_code, 404)
        item = self.enqueue().json()["data"]; self.process(item["id"])
        self.assertEqual(self.request("GET", f"/v1/workspaces/ws2/images/{item['id']}/content").status_code, 404)
        self.assertEqual(self.request("GET", f"/v1/workspaces/ws/images/{item['id']}/content", token="other").status_code, 403)
        self.assertEqual(self.request("GET", "/v1/workspaces/ws2/images").json()["data"], [])

    def test_invalid_input_and_raster_validation(self):
        for options in ({"prompt": " "}, {"aspect_ratio": "20:1"}, {"prompt": "x" * 4001}):
            self.assertEqual(self.enqueue(**options).status_code, 422)
        response = self.request("POST", "/v1/workspaces/ws/conversations/conv/images", data={"prompt": "edit", "request_key": "bad"}, files={"image": ("../../payload.png", b"<script>bad</script>", "image/png")})
        self.assertEqual(response.status_code, 422)
        for content in (b"<svg/>", b"x" * (MAX_IMAGE_BYTES + 1)):
            with self.assertRaises(ValueError): normalize_image(content)
        with self.assertRaises(ValueError): image_storage(self.config).read("../../outside")

    def test_upload_edit_and_iterative_context_remain_in_conversation(self):
        response = self.request("POST", "/v1/workspaces/ws/conversations/conv/images", data={"prompt": "Darker sky", "request_key": "edit"}, files={"image": ("../../photo.png", png(), "image/png")})
        self.assertEqual(response.status_code, 202, response.text)
        item = response.json()["data"]; self.process(item["id"])
        self.assertIsNotNone(self.provider.generate.call_args.args[0].source)
        followup = self.enqueue(key="followup", source_id=item["id"], prompt="Wider city").json()["data"]
        self.process(followup["id"])
        self.assertIn("Darker sky", self.provider.generate.call_args.args[0].prompt)
        self.assertIn("Wider city", self.provider.generate.call_args.args[0].prompt)

    def test_failure_retry_exhaustion_and_sanitization(self):
        self.provider.generate.side_effect = RuntimeError("SECRET provider response")
        item = self.enqueue().json()["data"]
        for attempt in range(3):
            self.process(item["id"])
            response = self.request("GET", "/v1/workspaces/ws/images")
            self.assertNotIn("SECRET", response.text)
            self.assertEqual(response.json()["data"][0]["status"], "failed")
            retry = self.request("POST", f"/v1/workspaces/ws/images/{item['id']}/retry")
            self.assertEqual(retry.status_code, 200 if attempt < 2 else 409)
        self.assertFalse(response.json()["data"][0]["can_retry"])

    def test_recovery_and_only_author_can_retry_or_cancel(self):
        item = self.enqueue().json()["data"]
        path = f"/v1/workspaces/ws/images/{item['id']}"
        shared = self.request("GET", "/v1/workspaces/ws/images", token="collaborator").json()["data"][0]
        self.assertFalse(shared["can_cancel"])
        self.assertEqual(self.request("POST", path + "/cancel", token="collaborator").status_code, 403)
        self.provider.generate.side_effect = RuntimeError("transient")
        self.process(item["id"])
        shared = self.request("GET", "/v1/workspaces/ws/images", token="collaborator").json()["data"][0]
        self.assertFalse(shared["can_retry"])
        self.assertEqual(self.request("POST", path + "/retry", token="collaborator").status_code, 403)
        self.provider.generate.side_effect = None
        self.assertEqual(self.request("POST", path + "/retry").status_code, 200)
        self.process(item["id"])
        self.assertEqual(self.request("GET", path + "/content").status_code, 200)

    def test_queue_bound_cancel_and_reconciliation(self):
        items = [self.enqueue(key=f"r-{i}").json()["data"] for i in range(3)]
        self.assertEqual(self.enqueue(key="fourth").status_code, 429)
        path = f"/v1/workspaces/ws/images/{items[0]['id']}"
        self.assertEqual(self.request("GET", path + "/content").status_code, 409)
        self.assertEqual(self.request("POST", path + "/cancel").json()["data"]["status"], "cancelled")
        self.assertFalse(self.process(items[0]["id"]))
        with self.factory() as db:
            job = db.get(ImageArtifact, items[1]["id"])
            job.status = "generating"; job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=11); db.commit()
            self.assertEqual(reconcile_images(db), 1)
            db.refresh(job); self.assertEqual(job.status, "failed")
        self.provider.generate.assert_not_called()

    def test_worker_rechecks_revoked_membership_before_paid_provider(self):
        item = self.enqueue().json()["data"]
        with self.factory() as db:
            db.query(Membership).filter_by(user_id="owner").delete(); db.commit()
        self.process(item["id"])
        self.provider.generate.assert_not_called()

    def test_natural_explicit_intent_uses_same_queue_and_message_contract(self):
        for prompt in ["Generate an image of a city", "Crée une image de TRIDENT", "Génère une illustration céleste"]:
            self.assertTrue(image_intent(prompt))
        self.assertFalse(image_intent("Can you explain how image generation works?"))
        response = self.request("POST", "/v1/workspaces/ws/conversations/conv/messages", json={"content": "Generate an image of a city", "request_key": "natural"})
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()["data"]
        self.assertEqual(result["image"]["status"], "queued")
        self.assertEqual(result["user_message"]["role"], "user")

    def test_natural_edit_targets_latest_authorized_image_only(self):
        self.assertTrue(image_edit_intent("Modifie cette image avec un ciel sombre"))
        self.assertFalse(image_edit_intent("Modifie le texte précédent"))
        path = "/v1/workspaces/ws/conversations/conv/messages"
        payload = {"content": "Modifie cette image avec un ciel sombre", "request_key": "edit-natural"}
        self.assertEqual(self.request("POST", path, json=payload).status_code, 409)
        parent = self.enqueue().json()["data"]; self.process(parent["id"])
        response = self.request("POST", path, json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["image"]["source_id"], parent["id"])

    def test_invalid_provider_output_never_becomes_viewable(self):
        self.provider.generate.return_value = ImageGenerationResult(b"<svg>unsafe</svg>", "test", "test")
        item = self.enqueue().json()["data"]; self.process(item["id"])
        self.assertEqual(self.request("GET", f"/v1/workspaces/ws/images/{item['id']}/content").status_code, 409)
        with self.factory() as db:
            record = db.get(ImageArtifact, item["id"])
            self.assertEqual(record.status, "failed"); self.assertIsNone(record.output_key)

    def test_provider_metadata_and_upload_path_are_not_client_assignable(self):
        response = self.enqueue(provider="forged", status="completed", output_key="../../secret", workspace_id="secret")
        self.assertEqual(response.status_code, 202)
        item = response.json()["data"]
        self.assertEqual(item["workspace_id"], "ws"); self.assertEqual(item["status"], "queued")
        with self.factory() as db:
            stored = db.get(ImageArtifact, item["id"])
            self.assertIsNone(stored.provider); self.assertIsNone(stored.output_key)

    def test_openai_boundary_uses_configured_model_generate_or_edit(self):
        client = Mock()
        response = SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(png()).decode())])
        client.images.generate.return_value = client.images.edit.return_value = response
        provider = OpenAIImageProvider(client, "configured-model")
        provider.generate(ImageGenerationRequest("City", "3:2"))
        self.assertEqual(client.images.generate.call_args.kwargs["size"], "1536x1024")
        self.assertEqual(client.images.generate.call_args.kwargs["model"], "configured-model")
        provider.generate(ImageGenerationRequest("Edit", "1:1", png()))
        client.images.edit.assert_called_once()


class ImageMigrationTests(unittest.TestCase):
    def test_additive_upgrade_and_explicit_empty_rollback_preserve_existing_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{directory}/migration.sqlite"
            config = Config("alembic.ini"); config.set_main_option("sqlalchemy.url", url)
            command.upgrade(config, "0010_document_lifecycle")
            engine = create_engine(url)
            with engine.begin() as db:
                db.execute(text("INSERT INTO workspaces (id,name) VALUES ('preserved','Original')"))
            command.upgrade(config, "head")
            self.assertTrue(inspect(engine).has_table("workspace_image_artifacts"))
            with self.assertRaisesRegex(RuntimeError, "non-downgradable"):
                command.downgrade(config, "0010_document_lifecycle")
            config.cmd_opts = argparse.Namespace(x=["allow_empty_image_downgrade=yes"])
            command.downgrade(config, "0010_document_lifecycle")
            self.assertFalse(inspect(engine).has_table("workspace_image_artifacts"))
            with engine.connect() as db:
                self.assertEqual(db.execute(text("SELECT name FROM workspaces WHERE id='preserved'")).scalar(), "Original")
            command.upgrade(config, "head")
            with engine.begin() as db:
                # Isolated SQLite fixture; explicit columns exercise the migrated schema.
                db.execute(text("INSERT INTO workspace_image_artifacts (id,workspace_id,conversation_id,message_id,user_message_id,user_id,request_key,request_hash,prompt,aspect_ratio,status,attempts) VALUES ('image','preserved','conv','msg','usrmsg','user','key','hash','City','1:1','queued',0)"))
            with self.assertRaisesRegex(RuntimeError, "destructive downgrade refused"):
                command.downgrade(config, "0010_document_lifecycle")
            with engine.connect() as db:
                self.assertEqual(db.execute(text("SELECT count(*) FROM workspace_image_artifacts")).scalar(), 1)
            engine.dispose()
