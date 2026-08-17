"""Stable contracts at the model-provider boundary."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ModelRequest:
    model: str
    messages: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class ModelResult:
    text: str
    provider_request_id: str | None = None


class ModelProvider(Protocol):
    def complete(self, request: ModelRequest) -> ModelResult: ...
