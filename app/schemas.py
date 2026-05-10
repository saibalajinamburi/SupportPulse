"""Pydantic schemas for the SupportPulse API request and response models."""

from pydantic import BaseModel, Field
from typing import Optional


class TicketRequest(BaseModel):
    """Incoming ticket payload for triage."""
    ticket_id: str = Field(default="", description="Optional ticket ID from source system")
    subject: str = Field(..., min_length=1, max_length=500, description="Ticket subject line")
    body: str = Field(..., min_length=1, max_length=10000, description="Ticket body/description")
    run_rag: bool = Field(default=True, description="Set False for fast routing-only mode (no response generation)")

    model_config = {"json_schema_extra": {
        "example": {
            "ticket_id": "T001",
            "subject": "Production API returning 500 errors",
            "body": "All endpoints down for 20 minutes. Revenue being lost.",
            "run_rag": True
        }
    }}


class ClassifyRequest(BaseModel):
    """Lightweight request for classification only."""
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10000)


class SimilarTicket(BaseModel):
    ticket_id: str
    similarity: float
    category: str
    priority: str
    subject: str


class ClassificationResult(BaseModel):
    category: str
    priority: str
    routing_team: str
    confidence: float
    model: str
    escalated: bool = False


class SLAResult(BaseModel):
    sla_risk_score: float
    breach_flag: bool
    risk_level: str


class TriageResponse(BaseModel):
    """Full triage response from the agent pipeline."""
    ticket_id: str
    subject: str
    classification: ClassificationResult
    sla_prediction: SLAResult
    routing_team: str
    auto_escalate: bool
    escalation_reason: str
    similar_tickets: list[SimilarTicket]
    grounded_response: Optional[str] = None
    timings_ms: dict
    total_ms: float


class ClassifyResponse(BaseModel):
    """Lightweight classification-only response."""
    category: str
    priority: str
    routing_team: str
    confidence: float
    model: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    llm_model: str
    fallback_model: str
    embed_model: str
    vector_index_size: int
    message: str
