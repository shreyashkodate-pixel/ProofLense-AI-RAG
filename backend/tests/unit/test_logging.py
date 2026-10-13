"""ProofLens AI — Unit Tests for Structured Logging & Secret Redaction.

Validates that API keys, passkeys, and database credentials are automatically
redacted from log records and formatting outputs.
"""

import json
import logging
from app.core.logging import JSONLogFormatter, redact_sensitive_text


def test_redact_sensitive_text_api_key():
    """Verify Gemini API keys are redacted."""
    raw = "Calling Gemini API with key AIzaSyDUMMYKEY1234567890abcdefghijklm"
    sanitized = redact_sensitive_text(raw)
    assert "AIzaSy" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_redact_sensitive_text_passkey():
    """Verify X-Workspace-Key headers are redacted."""
    raw = "Request failed with header X-Workspace-Key: super-secret-passkey-123"
    sanitized = redact_sensitive_text(raw)
    assert "super-secret-passkey-123" not in sanitized
    assert "[REDACTED_PASSKEY]" in sanitized


def test_redact_sensitive_text_db_url():
    """Verify database passwords in URLs are redacted."""
    raw = "Connecting to postgresql://admin:SuperSecretPassword123@db.supabase.co:5432/postgres"
    sanitized = redact_sensitive_text(raw)
    assert "SuperSecretPassword123" not in sanitized
    assert "[REDACTED_DB_PASS]" in sanitized


def test_json_log_formatter_output():
    """Verify JSONLogFormatter outputs valid parseable JSON."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="prooflens.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Service started on port 8000 with key AIzaSyABCDEF1234567890abcdefghijklmn",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "prooflens.test"
    assert "[REDACTED_API_KEY]" in parsed["message"]
    assert "AIzaSy" not in parsed["message"]
    assert "timestamp" in parsed
