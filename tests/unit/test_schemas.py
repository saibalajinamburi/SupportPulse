"""
Unit tests for FastAPI Pydantic schemas (Phase 7).
Validates all request/response models without starting the server.
"""
import pytest
from pydantic import ValidationError
from app.schemas import (
    TicketRequest, ClassifyRequest,
    ClassificationResult, SLAResult, SimilarTicket,
)


class TestTicketRequest:
    def test_valid_request(self):
        req = TicketRequest(
            ticket_id="T-001",
            subject="Server down",
            body="The API is returning 500 errors",
        )
        assert req.ticket_id == "T-001"
        assert req.run_rag is True  # default in schema

    def test_run_rag_default_is_true(self):
        req = TicketRequest(subject="test", body="test body")
        assert req.run_rag is True  # schema default

    def test_run_rag_can_be_overridden_to_false(self):
        req = TicketRequest(subject="test", body="test body", run_rag=False)
        assert req.run_rag is False

    def test_missing_subject_raises(self):
        with pytest.raises(ValidationError):
            TicketRequest(body="only body, no subject")

    def test_missing_body_raises(self):
        with pytest.raises(ValidationError):
            TicketRequest(subject="only subject, no body")


class TestClassifyRequest:
    def test_valid(self):
        req = ClassifyRequest(subject="Billing issue", body="Invoice wrong amount")
        assert req.subject == "Billing issue"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            ClassifyRequest(subject="only subject")


class TestClassificationResult:
    def test_valid(self):
        c = ClassificationResult(
            category="incident",
            priority="critical",
            routing_team="engineering",
            confidence=0.95,
            model="gemma2:2b",
            escalated=True,
        )
        assert c.category == "incident"
        assert c.confidence == 0.95

    def test_confidence_stored_as_float(self):
        c = ClassificationResult(
            category="bug", priority="high",
            routing_team="engineering",
            confidence=1, model="test", escalated=False,
        )
        assert isinstance(c.confidence, float)


class TestSLAResult:
    def test_valid(self):
        s = SLAResult(sla_risk_score=0.72, risk_level="medium", breach_flag=False)
        assert s.risk_level == "medium"
        assert s.sla_risk_score == 0.72


class TestSimilarTicket:
    def test_valid(self):
        t = SimilarTicket(
            ticket_id="OLD-001",
            subject="Similar issue",
            category="incident",
            priority="high",
            similarity=0.88,
        )
        assert t.similarity == 0.88


class TestSchemaDefaults:
    def test_ticket_id_defaults_to_empty_string(self):
        req = TicketRequest(subject="Test", body="Test body")
        assert req.ticket_id == ""
