import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import Base
from app.database.genesis_models import Workspace, WorkspaceDocument
from app.knowledge.jobs import claim_job, enqueue_ingestion, fail_job, finish_job
from app.knowledge.models import KnowledgeJob
from app.knowledge.storage import LocalObjectStorage
from app.tenancy.models import Organization


class DurableKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite://"); Base.metadata.create_all(self.engine)
        self.db=sessionmaker(bind=self.engine)()
        self.organization=Organization(name="Org",slug="knowledge-org",ownership_state="active")
        self.db.add(self.organization); self.db.flush()
        self.workspace=Workspace(name="Knowledge",organization_id=self.organization.id)
        self.db.add(self.workspace); self.db.flush()
        self.document=WorkspaceDocument(workspace_id=self.workspace.id,display_name="a.txt",storage_name="a.txt",storage_backend="local",storage_key=f"{self.workspace.id}/a.txt",media_type="text/plain",size_bytes=4,content_hash="a"*64,status="pending")
        self.db.add(self.document); self.db.commit()
    def tearDown(self): self.db.close(); self.engine.dispose()

    def test_storage_is_atomic_hashed_and_path_confined(self):
        with tempfile.TemporaryDirectory() as directory:
            storage=LocalObjectStorage(Path(directory)); stored=storage.put("workspace/document.txt",b"data")
            self.assertEqual(stored.etag,"3a6eb0790f39ac87c94f3856b2dd2c5d110e6811602261a9a923d3bb23adc8b7")
            self.assertEqual(storage.read(stored.key),b"data")
            with self.assertRaises(ValueError): storage.put("../escape",b"bad")
            storage.delete(stored.key); self.assertFalse(storage.exists(stored.key))

    def test_job_idempotency_lease_retry_and_completion(self):
        first=enqueue_ingestion(self.db,self.organization.id,self.workspace.id,self.document.id,1)
        second=enqueue_ingestion(self.db,self.organization.id,self.workspace.id,self.document.id,1)
        self.assertEqual(first.id,second.id); self.db.commit()
        claimed=claim_job(self.db,first.id,"worker-a",60); self.assertEqual(claimed.attempts,1)
        self.assertIsNone(claim_job(self.db,first.id,"worker-b",60))
        fail_job(self.db,claimed,"temporary"); self.assertEqual(claimed.status,"queued")
        claimed.lease_expires_at=None; claimed.available_at=claimed.created_at; self.db.commit()
        reclaimed=claim_job(self.db,first.id,"worker-b",60); finish_job(self.db,reclaimed)
        self.assertEqual(self.db.get(KnowledgeJob,first.id).status,"succeeded")
