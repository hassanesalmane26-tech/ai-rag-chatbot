"""Minimal privacy-safe structured logging for the backend foundation."""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event_name": getattr(record, "event_name", record.getMessage()),
        }
        for key in ("request_id", "method", "route", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler._trident_handler = True
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]
    for noisy_logger in ("httpx", "httpcore", "sqlalchemy.engine", "chromadb"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
