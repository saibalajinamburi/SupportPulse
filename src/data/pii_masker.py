"""PII Masking Module — src/data/pii_masker.py"""

import re
from typing import Tuple, List

# ── Regex Patterns ──────────────────────────────────────────────────────────
# ORDER MATTERS: More specific patterns must come BEFORE more general ones.
# account_id/ticket_id must run before phone, because the phone regex is
# greedy and will match "USR-12345" as a phone number fragment otherwise.
_PATTERNS = [
    # Email addresses (most common PII in support tickets)
    (
        "email",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE),
        "[EMAIL_REDACTED]",
    ),
    # Account / User IDs (USR-12345, ACC-98765, UID-001) — BEFORE phone (more specific)
    (
        "account_id",
        re.compile(r"\b(USR|ACC|USER|ACCOUNT|UID|CID|CUST)[-_]?\d{3,10}\b", re.IGNORECASE),
        "[ACCOUNT_REDACTED]",
    ),
    # Ticket/Case IDs (TKT-12345, CASE-0001, REF-ABC123) — BEFORE phone
    (
        "ticket_id",
        re.compile(r"\b(TKT|TICKET|CASE|REF|INC|SR|CHG)[-_]?[A-Z0-9]{3,12}\b", re.IGNORECASE),
        "[TICKET_ID_REDACTED]",
    ),
    # International phone numbers (+1-555-123-4567, 0049-123-456789, (555) 123-4567)
    # Runs AFTER account/ticket IDs to avoid greedy false positives
    (
        "phone",
        re.compile(
            r"(\+?\d{1,3}[\s\-]?)?(\(?\d{1,4}\)?[\s\-]?)\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}",
            re.IGNORECASE,
        ),
        "[PHONE_REDACTED]",
    ),
    # API keys and tokens (long alphanumeric strings 32+ chars, often hex or base64)
    (
        "api_key",
        re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"),
        "[API_KEY_REDACTED]",
    ),
    # IPv4 addresses
    (
        "ip_address",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "[IP_REDACTED]",
    ),
]


def mask_pii(text: str) -> Tuple[str, List[str]]:
    """Mask PII from text."""
    if not isinstance(text, str) or not text.strip():
        return text, []

    pii_found: List[str] = []
    masked = text

    for pii_type, pattern, replacement in _PATTERNS:
        if pattern.search(masked):
            masked = pattern.sub(replacement, masked)
            pii_found.append(pii_type)

    return masked, pii_found
