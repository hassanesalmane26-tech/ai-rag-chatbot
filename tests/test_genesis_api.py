import asyncio
import io
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Must be set before importing the application settings.
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / 'trident_genesis_tests.sqlite'}"
os.environ["OPENAI_API_KEY"] = "test-key"

import httpx
import uvicorn
from fastapi import UploadFile
from langchain_core.documents import Document

from app.main import app
from app.database.database import Base, SessionLocal, engine
from app.database.genesis_models import Workspace, WorkspaceDocument
from app.database.schema import HEAD_REVISION
from app.knowledge.service import MAX_UPLOAD_BYTES, create_document, delete_document
from app.knowledge.reconciliation import audit_workspace_knowledge
from app.rag.search import search_workspace_documents
from app.modules.registry import modules_for_edition
from app.tenancy.models import Organization


class InMemoryVectorStore:
    """Deterministic vector-store substitute for end-to-end domain tests."""

    def __init__(self):
        self.documents = []

    def add_documents(self, documents, ids=None):
        for document, identifier in zip(documents, ids or [None] * len(documents)):
            document.metadata["_test_vector_id"] = identifier
            self.documents.append(document)

    def delete(self, where):
        self.documents = [doc for doc in self.documents if doc.metadata.get("document_id") != where.get("document_id")]

    def similarity_search_with_relevance_scores(self, _query, k=5, filter=None):
        filtered = [doc for doc in self.documents if all(doc.metadata.get(key) == value for key, value in (filter or {}).items())]
        return [(doc, 1.0) for doc in filtered[:k]]


class AppClient:
    """Exercise the ASGI application through the same Uvicorn boundary as runtime."""

    def __init__(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        self.port = listener.getsockname()[1]
        listener.close()
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="error")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started and self.thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not self.server.started:
            raise RuntimeError("Le serveur de test Uvicorn n'a pas démarré.")
        self.client = httpx.Client(
            base_url=f"http://127.0.0.1:{self.port}",
            timeout=30,
            limits=httpx.Limits(max_keepalive_connections=0),
        )

    def request(self, method, url, **kwargs):
        return self.client.request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def close(self):
        self.client.close()
        self.server.should_exit = True
        self.thread.join(timeout=10)


class GenesisApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = AppClient()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def workspace(self, name="Workspace de test"):
        response = self.client.post("/v1/workspaces", json={"name": name})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["data"]

    def test_bootstraps_workspace_and_returns_overview(self):
        response = self.client.get("/v1/workspaces")
        self.assertEqual(response.status_code, 200, response.text)
        workspace = response.json()["data"][0]
        overview = self.client.get(f"/v1/workspaces/{workspace['id']}/overview")
        self.assertEqual(overview.status_code, 200, overview.text)
        self.assertEqual(
            overview.json()["data"]["metrics"],
            {"conversations": 0, "documents": 0, "messages": 0, "memories": 0},
        )
        self.assertEqual(
            [module["id"] for module in overview.json()["data"]["modules"]],
            ["home", "conversations", "knowledge", "memory"],
        )

    def test_identity_and_tenant_administration_are_not_public_in_ai1(self):
        schema = self.client.get("/openapi.json")
        self.assertEqual(schema.status_code, 200, schema.text)
        paths = schema.json()["paths"]
        self.assertFalse(any("/users" in path for path in paths))
        self.assertFalse(any("/organizations" in path for path in paths))
        self.assertFalse(any("/memberships" in path for path in paths))

    def test_module_registry_is_stable_and_workspace_scoped(self):
        workspace = self.workspace("Module registry")
        response = self.client.get(f"/v1/workspaces/{workspace['id']}/modules")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["meta"]["edition"], "genesis")
        identifiers = [module["id"] for module in response.json()["data"]]
        self.assertEqual(identifiers, ["home", "conversations", "knowledge", "memory"])
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(
            [module.order for module in modules_for_edition()], sorted(module.order for module in modules_for_edition())
        )
        missing = self.client.get("/v1/workspaces/not-found/modules")
        self.assertEqual(missing.status_code, 404, missing.text)

    def test_health_and_request_correlation_contracts(self):
        live = self.client.get("/health/live", headers={"x-request-id": "request-test-123"})
        self.assertEqual(live.status_code, 200, live.text)
        self.assertEqual(live.headers["x-request-id"], "request-test-123")
        ready = self.client.get("/health/ready")
        self.assertEqual(ready.status_code, 200, ready.text)
        self.assertEqual(ready.json(), {"status": "ready", "checks": {"database": "ok"}})
        build = self.client.get("/health/build")
        self.assertEqual(build.status_code, 200, build.text)
        self.assertEqual(build.json()["migration_head"], HEAD_REVISION)
        self.assertEqual(build.json()["migration_revision"], "unmanaged")

    def test_error_contract_generates_a_safe_request_id(self):
        missing = self.client.get("/v1/workspaces/not-found", headers={"x-request-id": "invalid id"})
        self.assertEqual(missing.status_code, 404, missing.text)
        payload = missing.json()["error"]
        self.assertEqual(payload["code"], "RESOURCE_NOT_FOUND")
        self.assertTrue(payload["request_id"])
        self.assertEqual(missing.headers["x-request-id"], payload["request_id"])

    def test_workspace_identity_is_stable_and_can_be_read(self):
        workspace = self.workspace("Identité durable")
        fetched = self.client.get(f"/v1/workspaces/{workspace['id']}")
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], workspace["id"])
        listed = self.client.get("/v1/workspaces")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(workspace["id"], [item["id"] for item in listed.json()["data"]])

        db = SessionLocal()
        try:
            persisted = db.get(Workspace, workspace["id"])
            self.assertIsNotNone(persisted.organization_id)
            self.assertNotIn("organization_id", workspace)
            organization = db.get(Organization, persisted.organization_id)
            self.assertEqual(organization.ownership_state, "legacy_unclaimed")
        finally:
            db.close()

    def test_workspace_can_be_renamed_without_losing_description(self):
        created = self.client.post(
            "/v1/workspaces", json={"name": "Avant", "description": "Description durable"}
        )
        self.assertEqual(created.status_code, 201, created.text)
        workspace = created.json()["data"]
        updated = self.client.patch(
            f"/v1/workspaces/{workspace['id']}", json={"name": "Après"}
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["data"]["name"], "Après")
        self.assertEqual(updated.json()["data"]["description"], "Description durable")

    def test_workspace_update_rejects_invalid_or_unknown_workspaces(self):
        workspace = self.workspace()
        invalid = self.client.patch(f"/v1/workspaces/{workspace['id']}", json={"name": "   "})
        self.assertEqual(invalid.status_code, 422, invalid.text)
        empty = self.client.patch(f"/v1/workspaces/{workspace['id']}", json={})
        self.assertEqual(empty.status_code, 422, empty.text)
        missing = self.client.get("/v1/workspaces/not-a-workspace")
        self.assertEqual(missing.status_code, 404, missing.text)
        unknown_update = self.client.patch("/v1/workspaces/not-a-workspace", json={"name": "Inconnu"})
        self.assertEqual(unknown_update.status_code, 404, unknown_update.text)

    def test_conversations_and_messages_are_isolated_by_workspace(self):
        first, second = self.workspace("Premier"), self.workspace("Second")
        created = self.client.post(f"/v1/workspaces/{first['id']}/conversations", json={"title": "Privée"})
        self.assertEqual(created.status_code, 201, created.text)
        conversation = created.json()["data"]

        denied = self.client.get(f"/v1/workspaces/{second['id']}/conversations/{conversation['id']}")
        self.assertEqual(denied.status_code, 404, denied.text)
        visible = self.client.get(f"/v1/workspaces/{first['id']}/conversations")
        self.assertEqual([item["id"] for item in visible.json()["data"]], [conversation["id"]])

    def test_message_persists_reply_and_citations(self):
        workspace = self.workspace()
        conversation = self.client.post(f"/v1/workspaces/{workspace['id']}/conversations", json={}).json()["data"]
        citations = [{"document_id": "doc-1", "document_name": "guide.txt", "excerpt": "TRIDENT"}]
        provider = MagicMock()
        provider.return_value.responses.create.return_value.output_text = "Réponse ancrée."
        with patch("app.conversations.service.build_citations", return_value=("Contexte", citations)), patch("app.conversations.service.OpenAI", provider):
            response = self.client.post(
                f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}/messages",
                json={"content": "Que sait ce Workspace ?"},
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["citations"], citations)
        self.assertEqual(response.json()["data"]["user_message"]["content"], "Que sait ce Workspace ?")
        self.assertEqual(response.json()["data"]["user_message"]["role"], "user")
        self.assertEqual(response.json()["data"]["role"], "assistant")
        detail = self.client.get(f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}")
        self.assertEqual([message["role"] for message in detail.json()["data"]["messages"]], ["user", "assistant"])

    def test_memory_crud_and_isolation_are_workspace_scoped(self):
        first, second = self.workspace("Memory owner"), self.workspace("Memory denied")
        created = self.client.post(
            f"/v1/workspaces/{first['id']}/memories",
            json={"kind": "preference", "title": "Langue", "content": "Répondre en français."},
        )
        self.assertEqual(created.status_code, 201, created.text)
        memory = created.json()["data"]
        self.assertTrue(memory["active"])
        self.assertEqual(
            self.client.get(f"/v1/workspaces/{second['id']}/memories").json()["data"], []
        )
        denied = self.client.patch(
            f"/v1/workspaces/{second['id']}/memories/{memory['id']}",
            json={"active": False},
        )
        self.assertEqual(denied.status_code, 404, denied.text)
        updated = self.client.patch(
            f"/v1/workspaces/{first['id']}/memories/{memory['id']}",
            json={"active": False, "title": "Langue principale"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertFalse(updated.json()["data"]["active"])
        deleted = self.client.request(
            "DELETE", f"/v1/workspaces/{first['id']}/memories/{memory['id']}"
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)

    def test_memory_conversation_scope_and_chat_context(self):
        first, second = self.workspace("Memory chat"), self.workspace("Other")
        conversation = self.client.post(
            f"/v1/workspaces/{first['id']}/conversations", json={}
        ).json()["data"]
        wrong_scope = self.client.post(
            f"/v1/workspaces/{second['id']}/memories",
            json={
                "title": "Interdite",
                "content": "Ne doit jamais traverser le Workspace.",
                "conversation_id": conversation["id"],
            },
        )
        self.assertEqual(wrong_scope.status_code, 404, wrong_scope.text)
        created = self.client.post(
            f"/v1/workspaces/{first['id']}/memories",
            json={
                "kind": "fact",
                "title": "Projet",
                "content": "TRIDENT est Workspace-centric.",
                "conversation_id": conversation["id"],
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        provider = MagicMock()
        provider.return_value.responses.create.return_value.output_text = "Compris."
        with patch("app.conversations.service.build_citations", return_value=("", [])), patch(
            "app.conversations.service.OpenAI", provider
        ):
            response = self.client.post(
                f"/v1/workspaces/{first['id']}/conversations/{conversation['id']}/messages",
                json={"content": "Quel est le projet ?"},
            )
        self.assertEqual(response.status_code, 201, response.text)
        provider_input = provider.return_value.responses.create.call_args.kwargs["input"]
        self.assertIn("TRIDENT est Workspace-centric.", provider_input[0]["content"])
        self.assertIn("données non fiables", provider_input[0]["content"])

    def test_message_rejects_blank_content_and_cross_workspace_access(self):
        first, second = self.workspace("Premier"), self.workspace("Second")
        conversation = self.client.post(f"/v1/workspaces/{first['id']}/conversations", json={}).json()["data"]
        blank = self.client.post(
            f"/v1/workspaces/{first['id']}/conversations/{conversation['id']}/messages",
            json={"content": "   "},
        )
        self.assertEqual(blank.status_code, 422, blank.text)
        denied = self.client.post(
            f"/v1/workspaces/{second['id']}/conversations/{conversation['id']}/messages",
            json={"content": "Interdit"},
        )
        self.assertEqual(denied.status_code, 404, denied.text)

    def test_provider_failure_keeps_user_message_in_workspace_history(self):
        workspace = self.workspace()
        conversation = self.client.post(f"/v1/workspaces/{workspace['id']}/conversations", json={}).json()["data"]
        with patch("app.conversations.service.build_citations", return_value=("", [])), patch(
            "app.conversations.service.OpenAI", side_effect=RuntimeError("offline")
        ):
            failed = self.client.post(
                f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}/messages",
                json={"content": "Message durable"},
            )
        self.assertEqual(failed.status_code, 503, failed.text)
        detail = self.client.get(f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}")
        self.assertEqual([message["content"] for message in detail.json()["data"]["messages"]], ["Message durable"])

    def test_rag_failure_is_controlled_and_keeps_user_message(self):
        workspace = self.workspace()
        conversation = self.client.post(f"/v1/workspaces/{workspace['id']}/conversations", json={}).json()["data"]
        with patch("app.conversations.service.build_citations", side_effect=RuntimeError("index offline")):
            failed = self.client.post(
                f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}/messages",
                json={"content": "Question durable"},
            )
        self.assertEqual(failed.status_code, 503, failed.text)
        self.assertEqual(failed.json()["error"]["code"], "DEPENDENCY_UNAVAILABLE")
        self.assertNotIn("index offline", failed.text)
        detail = self.client.get(f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}")
        self.assertEqual([message["content"] for message in detail.json()["data"]["messages"]], ["Question durable"])

    def test_document_upload_rejects_unsupported_type_and_wrong_workspace_cannot_see_metadata(self):
        first, second = self.workspace("Premier"), self.workspace("Second")
        rejected = self.client.post(
            f"/v1/workspaces/{first['id']}/documents",
            files={"file": ("unsafe.exe", b"not a document", "application/octet-stream")},
        )
        self.assertEqual(rejected.status_code, 415, rejected.text)
        db = SessionLocal()
        try:
            document = WorkspaceDocument(
                workspace_id=first["id"], display_name="guide.txt", storage_name="safe.txt",
                media_type="text/plain", size_bytes=5, status="indexed",
            )
            db.add(document)
            db.commit()
        finally:
            db.close()
        second_documents = self.client.get(f"/v1/workspaces/{second['id']}/documents")
        self.assertEqual(second_documents.status_code, 200, second_documents.text)
        self.assertEqual(second_documents.json()["data"], [])

    def test_document_upload_rejects_empty_content(self):
        workspace = self.workspace()
        rejected = self.client.post(
            f"/v1/workspaces/{workspace['id']}/documents",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["error"]["code"], "UNPROCESSABLE_ENTITY")
        listed = self.client.get(f"/v1/workspaces/{workspace['id']}/documents")
        self.assertEqual(listed.json()["data"], [])

    def test_document_upload_rejects_content_above_limit(self):
        workspace = self.workspace()
        rejected = self.client.post(
            f"/v1/workspaces/{workspace['id']}/documents",
            files={"file": ("too-large.txt", b"x" * (MAX_UPLOAD_BYTES + 1), "text/plain")},
        )
        self.assertEqual(rejected.status_code, 413, rejected.text)
        self.assertEqual(rejected.json()["error"]["code"], "PAYLOAD_TOO_LARGE")
        listed = self.client.get(f"/v1/workspaces/{workspace['id']}/documents")
        self.assertEqual(listed.json()["data"], [])

    def test_document_delete_is_scoped_to_its_workspace(self):
        first, second = self.workspace("Premier"), self.workspace("Second")
        db = SessionLocal()
        try:
            document = WorkspaceDocument(
                workspace_id=first["id"], display_name="private.txt", storage_name="private.txt",
                media_type="text/plain", size_bytes=7, status="indexed",
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            document_id = document.id
        finally:
            db.close()

        denied = self.client.request(
            "DELETE", f"/v1/workspaces/{second['id']}/documents/{document_id}"
        )
        self.assertEqual(denied.status_code, 404, denied.text)
        still_visible = self.client.get(f"/v1/workspaces/{first['id']}/documents")
        self.assertEqual([item["id"] for item in still_visible.json()["data"]], [document_id])

        with tempfile.TemporaryDirectory() as tempdir, patch(
            "app.knowledge.service.DOCUMENTS_ROOT", Path(tempdir)
        ), patch("app.knowledge.service.vectorstore"):
            deleted = self.client.request(
                "DELETE", f"/v1/workspaces/{first['id']}/documents/{document_id}"
            )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["data"], {"id": document_id, "deleted": True})
        self.assertEqual(self.client.get(f"/v1/workspaces/{first['id']}/documents").json()["data"], [])

    def test_document_upload_is_idempotent_by_workspace_content(self):
        workspace = self.workspace("Idempotence")
        vector = InMemoryVectorStore()
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "app.knowledge.service.DOCUMENTS_ROOT", Path(tempdir)
        ), patch("app.knowledge.service.vectorstore", vector):
            first = self.client.post(
                f"/v1/workspaces/{workspace['id']}/documents",
                files={"file": ("first.txt", b"same durable content", "text/plain")},
            )
            second = self.client.post(
                f"/v1/workspaces/{workspace['id']}/documents",
                files={"file": ("renamed.txt", b"same durable content", "text/plain")},
            )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(first.json()["data"]["id"], second.json()["data"]["id"])
        listed = self.client.get(f"/v1/workspaces/{workspace['id']}/documents")
        self.assertEqual(len(listed.json()["data"]), 1)
        self.assertEqual(len(vector.documents), 1)

    def test_failed_ingestion_preserves_original_and_can_be_retried(self):
        workspace = self.workspace("Retry")
        failing_vector = MagicMock()
        failing_vector.add_documents.side_effect = RuntimeError("index offline")
        with tempfile.TemporaryDirectory() as tempdir, patch(
            "app.knowledge.service.DOCUMENTS_ROOT", Path(tempdir)
        ), patch("app.knowledge.service.vectorstore", failing_vector):
            failed = self.client.post(
                f"/v1/workspaces/{workspace['id']}/documents",
                files={"file": ("retry.txt", b"retryable content", "text/plain")},
            )
            self.assertEqual(failed.status_code, 503, failed.text)
            listed = self.client.get(f"/v1/workspaces/{workspace['id']}/documents").json()["data"]
            self.assertEqual(len(listed), 1)
            document = listed[0]
            self.assertEqual(document["status"], "failed")
            stored = Path(tempdir) / workspace["id"] / next(
                path.name for path in (Path(tempdir) / workspace["id"]).iterdir()
            )
            self.assertTrue(stored.exists())

            recovered_vector = InMemoryVectorStore()
            with patch("app.knowledge.service.vectorstore", recovered_vector):
                retried = self.client.post(
                    f"/v1/workspaces/{workspace['id']}/documents/{document['id']}/retry"
                )
            self.assertEqual(retried.status_code, 200, retried.text)
            self.assertEqual(retried.json()["data"]["status"], "indexed")
            self.assertEqual(retried.json()["data"]["ingestion_attempts"], 2)
            self.assertEqual(len(recovered_vector.documents), 1)

    def test_document_retry_is_scoped_to_workspace(self):
        first, second = self.workspace("Retry owner"), self.workspace("Retry denied")
        db = SessionLocal()
        try:
            document = WorkspaceDocument(
                workspace_id=first["id"],
                display_name="private.txt",
                storage_name="private.txt",
                media_type="text/plain",
                size_bytes=7,
                status="failed",
            )
            db.add(document)
            db.commit()
            document_id = document.id
        finally:
            db.close()
        denied = self.client.post(
            f"/v1/workspaces/{second['id']}/documents/{document_id}/retry"
        )
        self.assertEqual(denied.status_code, 404, denied.text)

    def test_knowledge_to_conversation_flow_keeps_workspace_scope_and_citations(self):
        workspace = self.workspace("Knowledge E2E")
        conversation = self.client.post(f"/v1/workspaces/{workspace['id']}/conversations", json={}).json()["data"]
        vector = InMemoryVectorStore()
        provider = MagicMock()
        provider.return_value.responses.create.return_value.output_text = "TRIDENT est un AI Operating System."
        with tempfile.TemporaryDirectory() as tempdir, patch("app.knowledge.service.DOCUMENTS_ROOT", Path(tempdir)), patch("app.knowledge.service.vectorstore", vector), patch("app.rag.search.vectorstore", vector), patch("app.conversations.service.OpenAI", provider):
            uploaded = self.client.post(
                f"/v1/workspaces/{workspace['id']}/documents",
                files={"file": ("vision.txt", b"TRIDENT est un AI Operating System centre sur le Workspace.", "text/plain")},
            )
            self.assertEqual(uploaded.status_code, 201, uploaded.text)
            document = uploaded.json()["data"]
            answered = self.client.post(
                f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}/messages",
                json={"content": "Quel est le role de TRIDENT ?"},
            )
        self.assertEqual(answered.status_code, 201, answered.text)
        self.assertEqual(answered.json()["data"]["citations"][0]["document_id"], document["id"])
        provider.return_value.responses.create.assert_called_once()


class KnowledgeServiceTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self.workspace = Workspace(name="Knowledge test")
        self.db.add(self.workspace)
        self.db.commit()
        self.db.refresh(self.workspace)
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_knowledge_storage_index_search_and_delete_are_scoped(self):
        upload = UploadFile(filename="guide.txt", file=io.BytesIO(b"TRIDENT Knowledge"))
        chunk = Document(page_content="TRIDENT Knowledge", metadata={})
        vector = MagicMock()
        with patch("app.knowledge.service.DOCUMENTS_ROOT", Path(self.tempdir.name)), patch("app.knowledge.service.load_document", return_value=[chunk]), patch("app.knowledge.service.split_documents", return_value=[chunk]), patch("app.knowledge.service.vectorstore", vector):
            document = asyncio.run(create_document(self.db, self.workspace.id, upload))
            stored = Path(self.tempdir.name) / self.workspace.id / document.storage_name
            self.assertTrue(stored.exists())
            self.assertEqual(document.status, "indexed")
            self.assertEqual(chunk.metadata["workspace_id"], self.workspace.id)
            self.assertEqual(chunk.metadata["document_id"], document.id)
            vector.add_documents.assert_called_once()
            indexed_chunks = vector.add_documents.call_args.args[0]
            indexed_ids = vector.add_documents.call_args.kwargs["ids"]
            self.assertEqual(indexed_chunks, [chunk])
            self.assertEqual(indexed_ids, [f"{document.id}:v1:0"])
            delete_document(self.db, document)
            self.assertFalse(stored.exists())
            self.assertEqual(vector.delete.call_count, 2)
            vector.delete.assert_called_with(where={"document_id": document.id})

    def test_search_always_filters_on_workspace_id(self):
        vector = MagicMock()
        vector.similarity_search_with_relevance_scores.return_value = []
        with patch("app.rag.search.vectorstore", vector):
            self.assertEqual(search_workspace_documents("workspace-a", "question"), [])
        vector.similarity_search_with_relevance_scores.assert_called_once_with(
            "question", k=5, filter={"workspace_id": "workspace-a"}
        )

    def test_partial_delete_preserves_metadata_and_original_for_retry(self):
        document = WorkspaceDocument(
            workspace_id=self.workspace.id,
            display_name="durable.txt",
            storage_name="durable.txt",
            media_type="text/plain",
            size_bytes=7,
            status="indexed",
        )
        self.db.add(document)
        self.db.commit()
        stored = Path(self.tempdir.name) / self.workspace.id / document.storage_name
        stored.parent.mkdir(parents=True)
        stored.write_bytes(b"durable")
        vector = MagicMock()
        vector.delete.side_effect = RuntimeError("vector unavailable")
        with patch("app.knowledge.service.DOCUMENTS_ROOT", Path(self.tempdir.name)), patch(
            "app.knowledge.service.vectorstore", vector
        ):
            with self.assertRaises(Exception):
                delete_document(self.db, document)
        self.assertTrue(stored.exists())
        preserved = self.db.get(WorkspaceDocument, document.id)
        self.assertIsNotNone(preserved)
        self.assertEqual(preserved.status, "delete_failed")

    def test_reconciliation_reports_drift_without_mutating_state(self):
        document = WorkspaceDocument(
            workspace_id=self.workspace.id,
            display_name="missing.txt",
            storage_name="missing.txt",
            media_type="text/plain",
            size_bytes=7,
            content_hash="0" * 64,
            status="indexed",
        )
        self.db.add(document)
        self.db.commit()
        vector = MagicMock()
        vector.get.return_value = {
            "ids": ["orphan:v1:0"],
            "metadatas": [{"workspace_id": self.workspace.id, "document_id": "orphan"}],
        }
        before = self.db.query(WorkspaceDocument).count()
        report = audit_workspace_knowledge(
            self.db,
            self.workspace.id,
            store=vector,
            documents_root=Path(self.tempdir.name),
        )
        self.assertFalse(report.consistent)
        self.assertEqual(
            {issue.kind for issue in report.issues},
            {"missing_original", "missing_vectors", "orphan_vectors"},
        )
        self.assertEqual(self.db.query(WorkspaceDocument).count(), before)
