"""Explicit document lifecycle and safe transition policy."""

from dataclasses import dataclass


UPLOADED = "uploaded"
PENDING_SCAN = "pending_scan"
SCANNING = "scanning"
SCAN_FAILED = "scan_failed"
REJECTED = "rejected"
PENDING_PROCESSING = "pending_processing"
PROCESSING = "processing"
INDEXED = "indexed"
PROCESSING_FAILED = "processing_failed"

READY_STATUSES = frozenset({INDEXED})
RETRYABLE_STATUSES = frozenset({SCAN_FAILED, PROCESSING_FAILED})
IN_FLIGHT_STATUSES = frozenset({PENDING_SCAN, SCANNING, PENDING_PROCESSING, PROCESSING})
TERMINAL_STATUSES = frozenset({INDEXED, REJECTED})

# Old rows remain processable after the additive migration and during rolling
# upgrades. These aliases are never emitted by the new API.
LEGACY_STATUS_ALIASES = {"pending": PENDING_SCAN, "failed": PROCESSING_FAILED}

ALLOWED_TRANSITIONS = {
    UPLOADED: {PENDING_SCAN, PROCESSING_FAILED},
    PENDING_SCAN: {SCANNING, SCAN_FAILED},
    SCANNING: {PENDING_PROCESSING, SCAN_FAILED, REJECTED},
    SCAN_FAILED: {PENDING_SCAN},
    PENDING_PROCESSING: {PROCESSING, PROCESSING_FAILED},
    PROCESSING: {INDEXED, PROCESSING_FAILED, REJECTED},
    PROCESSING_FAILED: {PENDING_SCAN, PENDING_PROCESSING},
    INDEXED: {PROCESSING_FAILED},
    REJECTED: set(),
}


class InvalidDocumentTransition(ValueError):
    pass


def canonical_status(status: str) -> str:
    return LEGACY_STATUS_ALIASES.get(status, status)


def transition_document(document, target: str, *, error: str | None = None) -> None:
    current = canonical_status(document.status)
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidDocumentTransition(f"Invalid document transition: {current} -> {target}")
    document.status = target
    document.error_message = error[:1000] if error else None


@dataclass(frozen=True, slots=True)
class DocumentStatusView:
    status: str
    ready: bool
    retryable: bool


def status_view(status: str) -> DocumentStatusView:
    normalized = canonical_status(status)
    return DocumentStatusView(
        status=normalized,
        ready=normalized in READY_STATUSES,
        retryable=normalized in RETRYABLE_STATUSES,
    )
