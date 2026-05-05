"""Unit Tests — PII Masker"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.pii_masker import mask_pii


def test_email_masked():
    text = "Contact john.doe@example.com for help."
    masked, flags = mask_pii(text)
    assert "[EMAIL_REDACTED]" in masked
    assert "john.doe@example.com" not in masked
    assert "email" in flags


def test_no_pii_unchanged():
    text = "The application crashed on login page."
    masked, flags = mask_pii(text)
    assert masked == text
    assert flags == []


def test_multiple_pii_types():
    text = "Email: user@company.com Account: USR-12345"
    masked, flags = mask_pii(text)
    assert "user@company.com" not in masked
    assert "USR-12345" not in masked
    assert "email" in flags
    assert "account_id" in flags


def test_ip_address_masked():
    text = "Server at 192.168.1.100 is down."
    masked, flags = mask_pii(text)
    assert "192.168.1.100" not in masked
    assert "ip_address" in flags


def test_empty_string():
    masked, flags = mask_pii("")
    assert flags == []


def test_none_safe():
    # Should handle non-string gracefully
    masked, flags = mask_pii(None)
    assert flags == []
