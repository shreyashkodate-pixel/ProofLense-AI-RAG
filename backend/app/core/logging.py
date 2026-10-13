"""ProofLens AI — Structured Logging & Redaction Engine.

Provides JSON-formatted structured logging with strict automated redaction
of sensitive credentials, passkeys, and document contents.
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict


# Sensitive patterns to redact
REDACTION_PATTERNS = [
    # Google API keys: AIza...
    (re.compile(r"AIza[0-9A-Za-z\-_]{16,}"), "[REDACTED_API_KEY]"),
    # Generic passkeys / tokens
    (re.compile(r"(X-Workspace-Key:\s*)([^\s,]+)", re.IGNORECASE), r"\1[REDACTED_PASSKEY]"),
    (re.compile(r"(Bearer\s+)([A-Za-z0-9\-_\.]+)", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    # DB connection passwords (e.g. postgresql://user:pass@host)
    (re.compile(r"(postgres(?:ql)?:\/\/[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1[REDACTED_DB_PASS]\3"),
    # Key-value secret patterns
    (re.compile(r"(token|secret|password|api_key|service_role_key)=([^\s&]+)", re.IGNORECASE), r"\1=[REDACTED]"),
]


def redact_sensitive_text(text: str) -> str:
    """Sanitize text by replacing sensitive keys and patterns with redaction placeholders."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern, replacement in REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class JSONLogFormatter(logging.Formatter):
    """Custom logging formatter that outputs JSON objects with redacted values."""

    def format(self, record: logging.LogRecord) -> str:
        # Format the log message safely
        message = record.getMessage()
        sanitized_message = redact_sensitive_text(message)

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitized_message,
        }

        # Include location details if warning/error
        if record.levelno >= logging.WARNING:
            log_payload["module"] = record.module
            log_payload["line"] = record.lineno

        # Include exception tracebacks if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_payload["exception"] = redact_sensitive_text(exc_text)

        # Include extra attributes if provided
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            # Sanitize dictionary values
            sanitized_extra = {}
            for k, v in record.extra.items():
                if isinstance(v, str):
                    sanitized_extra[k] = redact_sensitive_text(v)
                else:
                    sanitized_extra[k] = v
            log_payload["context"] = sanitized_extra

        return json.dumps(log_payload, default=str)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure structured logging for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(JSONLogFormatter())
    root_logger.addHandler(stream_handler)

    # Return app-specific logger
    app_logger = logging.getLogger("prooflens")
    app_logger.setLevel(level)
    return app_logger


# Default logger instance
logger = logging.getLogger("prooflens")
