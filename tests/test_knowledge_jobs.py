import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import Base
from app.database.genesis_models import Workspace, WorkspaceDocument
from app.identity import models as identity_models  # noqa: F401
from app.governance import models as governance_models  # noqa: F401
from app.knowledge.jobs import claim_job, enqueue_ingestion, fail_job, finish_job, requeue_ingestion
from app.knowledge.models import KnowledgeJob
from app.knowledge.storage import LocalObjectStorage
from app.knowledge.processing import NonRetryableProcessingError, process_document
from app.knowledge.reconciliation import reconcile_stuck_documents
from app.knowledge.scanner import ScanResult, ScanVerdict, ScannerUnavailable
from app.knowledge.state import InvalidDocumentTransition, canonical_status, transition_document
from app.tenancy.models import Organization


class DurableKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite://"); Base.metadata.create_all(self.engine)
        self.db=sessionmaker(bind=self.engine)()
        self.organization=Organization(name="Org",slug="knowledge-org",ownership_state="active")
        self.db.add(self.organization); self.db.flush()
        self.workspace=Workspace(name="Knowledge",organization_id=self.organization.id)
        self.db.add(self.workspace); self.db.flush()
        self.document=WorkspaceDocument(workspace_id=self.workspace.id,display_name="a.txt",storage_name="a.txt",storage_backend="local",storage_key=f"{self.workspace.id}/a.txt",media_type="text/plain",size_bytes=4,content_hash="a"*64,status="pending_scan")
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

    def test_retry_exhaustion_is_bounded(self):
        job = enqueue_ingestion(self.db, self.organization.id, self.workspace.id, self.document.id, 1)
        job.attempts = job.max_attempts
        job.status = "failed"
        self.db.commit()
        with self.assertRaises(ValueError):
            requeue_ingestion(self.db, job)

    def test_document_state_machine_rejects_invalid_transitions(self):
        transition_document(self.document, "scanning")
        with self.assertRaises(InvalidDocumentTransition):
            transition_document(self.document, "indexed")

    def test_legacy_document_statuses_map_to_the_new_lifecycle(self):
        self.assertEqual(canonical_status("pending"), "pending_scan")
        self.assertEqual(canonical_status("failed"), "processing_failed")

    def _process(self, scanner, store=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = LocalObjectStorage(Path(directory.name))
        storage.put(self.document.storage_key, b"safe text")
        vector = store or MagicMock()
        process_document(self.db, self.document, scanner=scanner, storage=storage, store=vector)
        return vector

    def test_safe_scan_processes_once_and_is_idempotent(self):
        scanner = MagicMock()
        scanner.scan.return_value = ScanResult(ScanVerdict.SAFE, "test")
        vector = self._process(scanner)
        self.assertEqual(self.document.status, "indexed")
        vector.add_documents.assert_called_once()
        process_document(self.db, self.document, scanner=scanner, store=vector)
        vector.add_documents.assert_called_once()
        scanner.scan.assert_called_once()

    def test_unsafe_and_unknown_scans_fail_closed(self):
        for verdict, expected in ((ScanVerdict.UNSAFE, "rejected"), (ScanVerdict.UNKNOWN, "scan_failed")):
            self.document.status = "pending_scan"
            self.db.commit()
            scanner = MagicMock()
            scanner.scan.return_value = ScanResult(verdict, "test")
            with self.assertRaises((NonRetryableProcessingError, RuntimeError)):
                self._process(scanner)
            self.assertEqual(self.document.status, expected)

    def test_scanner_technical_failure_is_retryable_and_fail_closed(self):
        scanner = MagicMock()
        scanner.scan.side_effect = ScannerUnavailable("offline")
        vector = MagicMock()
        with self.assertRaises(RuntimeError):
            self._process(scanner, vector)
        self.assertEqual(self.document.status, "scan_failed")
        vector.add_documents.assert_not_called()

    def test_index_failure_is_retryable_and_retry_can_finish(self):
        scanner = MagicMock()
        scanner.scan.return_value = ScanResult(ScanVerdict.SAFE, "test")
        failing = MagicMock()
        failing.add_documents.side_effect = RuntimeError("offline")
        with self.assertRaises(RuntimeError):
            self._process(scanner, failing)
        self.assertEqual(self.document.status, "processing_failed")
        recovered = MagicMock()
        self._process(scanner, recovered)
        self.assertEqual(self.document.status, "indexed")
        scanner.scan.assert_called_once()

    def test_permanently_corrupt_input_is_rejected_before_indexing(self):
        scanner = MagicMock()
        scanner.scan.return_value = ScanResult(ScanVerdict.SAFE, "test")
        vector = MagicMock()
        with patch("app.knowledge.processing.load_document", side_effect=UnicodeError("corrupt")):
            with self.assertRaises(NonRetryableProcessingError):
                self._process(scanner, vector)
        self.assertEqual(self.document.status, "rejected")
        vector.add_documents.assert_not_called()

    def test_reconciliation_requeues_stuck_processing(self):
        self.document.status = "processing"
        self.document.updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.db.commit()
        vector = MagicMock()
        vector.get.return_value = {"metadatas": []}
        actions = reconcile_stuck_documents(
            self.db, self.workspace.id, stale_after=timedelta(minutes=5),
            now=datetime.now(timezone.utc), store=vector,
        )
        self.assertEqual(len(actions), 1)
        self.assertTrue(actions[0].requeued)
        self.assertEqual(self.document.status, "processing_failed")

    def test_reconciliation_invalidates_ready_document_with_missing_original(self):
        self.document.status = "indexed"
        self.db.commit()
        vector = MagicMock()
        vector.get.return_value = {"metadatas": [{"document_id": self.document.id}]}
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        actions = reconcile_stuck_documents(
            self.db, self.workspace.id, store=vector,
            documents_root=Path(directory.name),
        )
        self.assertEqual(actions[0].previous_status, "indexed")
        self.assertFalse(actions[0].requeued)
        self.assertEqual(self.document.status, "processing_failed")
