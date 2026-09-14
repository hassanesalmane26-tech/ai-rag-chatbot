"""Provider-neutral malware scanning contract.

The deterministic adapter is suitable only for development and tests. Runtime
production activation must provide a real scanner adapter; unavailable or
indeterminate scans always fail closed.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol


class ScanVerdict(str, Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ScanResult:
    verdict: ScanVerdict
    engine: str
    detail: str | None = None


class MalwareScanner(Protocol):
    def scan(self, path: Path) -> ScanResult: ...


class ScannerUnavailable(RuntimeError):
    pass


class DeterministicDevelopmentScanner:
    """Small deterministic adapter; not a production malware engine."""

    engine = "deterministic-development"

    def scan(self, path: Path) -> ScanResult:
        content = path.read_bytes()
        # EICAR is intentionally recognized so the fail-closed path can be
        # exercised locally without introducing executable malware.
        if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
            return ScanResult(ScanVerdict.UNSAFE, self.engine, "test signature detected")
        return ScanResult(ScanVerdict.SAFE, self.engine)


class UnavailableScanner:
    def scan(self, _path: Path) -> ScanResult:
        raise ScannerUnavailable("No production malware scanner is configured")


def scanner_for_environment(environment: str) -> MalwareScanner:
    if environment in {"development", "test"}:
        return DeterministicDevelopmentScanner()
    return UnavailableScanner()
