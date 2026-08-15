import asyncio
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Must be set before importing the application settings.
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.gettempdir()) / 'trident_genesis_tests.sqlite'}"
os.environ["OPENAI_API_KEY"] = "test-key"

from fastapi.testclient import TestClient
from fastapi import UploadFile
from langchain_core.documents import Document

from app.main import app
from app.database.database import Base, SessionLocal, engine
from app.database.genesis_models import Workspace, WorkspaceDocument
from app.knowledge.service import create_document, delete_document
from app.rag.search import search_workspace_documents


class InMemoryVectorStore:
    """Deterministic vector-store substitute for end-to-end domain tests."""

    def __init__(self):
        self.documents = []

    def add_documents(self, documents):
        self.documents.extend(documents)

    def delete(self, where):
        self.documents = [doc for doc in self.documents if doc.metadata.get("document_id") != where.get("document_id")]

    def similarity_search_with_relevance_scores(self, _query, k=5, filter=None):
        filtered = [doc for doc in self.documents if all(doc.metadata.get(key) == value for key, value in (filter or {}).items())]
        return [(doc, 1.0) for doc in filtered[:k]]


class GenesisApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

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
        self.assertEqual(overview.json()["data"]["metrics"], {"conversations": 0, "documents": 0, "messages": 0})

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
        with patch("app.api.genesis.build_citations", return_value=("Contexte", citations)), patch("app.api.genesis.OpenAI", provider):
            response = self.client.post(
                f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}/messages",
                json={"content": "Que sait ce Workspace ?"},
            )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["citations"], citations)
        detail = self.client.get(f"/v1/workspaces/{workspace['id']}/conversations/{conversation['id']}")
        self.assertEqual([message["role"] for message in detail.json()["data"]["messages"]], ["user", "assistant"])

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

    def test_knowledge_to_conversation_flow_keeps_workspace_scope_and_citations(self):
        workspace = self.workspace("Knowledge E2E")
        conversation = self.client.post(f"/v1/workspaces/{workspace['id']}/conversations", json={}).json()["data"]
        vector = InMemoryVectorStore()
        provider = MagicMock()
        provider.return_value.responses.create.return_value.output_text = "TRIDENT est un AI Operating System."
        with tempfile.TemporaryDirectory() as tempdir, patch("app.knowledge.service.DOCUMENTS_ROOT", Path(tempdir)), patch("app.knowledge.service.vectorstore", vector), patch("app.rag.search.vectorstore", vector), patch("app.api.genesis.OpenAI", provider):
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
            vector.add_documents.assert_called_once_with([chunk])
            delete_document(self.db, document)
            self.assertFalse(stored.exists())
            vector.delete.assert_called_once_with(where={"document_id": document.id})

    def test_search_always_filters_on_workspace_id(self):
        vector = MagicMock()
        vector.similarity_search_with_relevance_scores.return_value = []
        with patch("app.rag.search.vectorstore", vector):
            self.assertEqual(search_workspace_documents("workspace-a", "question"), [])
        vector.similarity_search_with_relevance_scores.assert_called_once_with(
            "question", k=5, filter={"workspace_id": "workspace-a"}
        )
