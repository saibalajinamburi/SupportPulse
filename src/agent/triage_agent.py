"""
Triage Agent — deterministic orchestrator that routes every support ticket
using all intelligence layers: classifier, SLA predictor, retriever, and RAG.

Design philosophy: The agent is NOT a free-running autonomous agent (LangChain style).
It is a deterministic pipeline with explicit routing rules applied on top of LLM outputs.
This makes it reliable, auditable, and debuggable in production.
"""

import time
from dataclasses import dataclass, field, asdict

from src.models.classifier import classify_ticket
from src.models.sla_model import predict_sla_risk
from src.vector.retriever import retrieve_similar
from src.rag.pipeline import run_rag_pipeline
from app.config import settings


# --- Routing Rules ---
# Priority: (category, priority) → team + auto_escalate flag
# More specific rules take priority over default.
ROUTING_RULES = {
    ("incident",    "critical"): {"team": "engineering", "auto_escalate": True},
    ("incident",    "high"):     {"team": "engineering", "auto_escalate": False},
    ("bug",         "critical"): {"team": "engineering", "auto_escalate": True},
    ("bug",         "high"):     {"team": "engineering", "auto_escalate": False},
    ("security",    "critical"): {"team": "security",    "auto_escalate": True},
    ("security",    "high"):     {"team": "security",    "auto_escalate": True},
    ("security",    "medium"):   {"team": "security",    "auto_escalate": False},
    ("billing",     "critical"): {"team": "billing",     "auto_escalate": True},
    ("billing",     "high"):     {"team": "billing",     "auto_escalate": False},
    ("billing",     "medium"):   {"team": "billing",     "auto_escalate": False},
    ("performance", "critical"): {"team": "infra",       "auto_escalate": True},
    ("performance", "high"):     {"team": "infra",       "auto_escalate": False},
}
DEFAULT_ROUTING = {"team": "support", "auto_escalate": False}

# SLA breach risk threshold above which we force escalation regardless of priority
SLA_ESCALATION_THRESHOLD = 0.75


@dataclass
class AgentTriageResult:
    """Structured output from the triage agent — every field is auditable."""
    ticket_id: str
    subject: str

    # Classification
    category: str
    priority: str
    classification_confidence: float
    classification_model: str

    # SLA Prediction
    sla_breach_risk: float
    sla_escalated: bool

    # Routing Decision
    routing_team: str
    auto_escalate: bool
    escalation_reason: str

    # Context & Response
    similar_tickets: list
    grounded_response: str

    # Performance
    timings: dict = field(default_factory=dict)
    total_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def triage(
    subject: str,
    body: str,
    ticket_id: str = "",
    run_rag: bool = True,
) -> AgentTriageResult:
    """
    Run the full triage pipeline for one support ticket.

    Steps:
    1. Classify — LLM Cascade (fast primary + smart fallback)
    2. Predict SLA breach risk — LightGBM on structured features
    3. Retrieve — top-3 similar historical tickets from ChromaDB
    4. Route — apply deterministic routing rules
    5. Generate — RAG-grounded response (optional, skip for speed in batch)
    """
    start = time.time()
    timings = {}

    # 1. Classify
    t0 = time.time()
    clf = classify_ticket(
        subject=subject,
        body=body,
        model=settings.OLLAMA_LLM_MODEL,
        fallback_model=settings.OLLAMA_FALLBACK_MODEL,
    )
    timings["classify_ms"] = round((time.time() - t0) * 1000, 1)

    category = clf.get("category", "question")
    priority = clf.get("priority", "medium")
    routing_team_from_clf = clf.get("routing_team", "support")

    # 2. SLA Breach Prediction
    t0 = time.time()
    sla_features = _extract_sla_features(subject, body)
    sla_result = predict_sla_risk(sla_features)
    sla_risk = sla_result["sla_risk_score"]
    timings["sla_ms"] = round((time.time() - t0) * 1000, 1)

    # 3. Retrieve similar tickets
    t0 = time.time()
    try:
        similar = retrieve_similar(f"{subject} {body}", top_k=3)
    except Exception:
        similar = []
    timings["retrieve_ms"] = round((time.time() - t0) * 1000, 1)

    # 4. Apply routing rules
    routing = ROUTING_RULES.get((category, priority), DEFAULT_ROUTING).copy()

    # SLA override: force escalation if breach risk is high regardless of priority
    sla_escalated = False
    if sla_risk >= SLA_ESCALATION_THRESHOLD and not routing["auto_escalate"]:
        routing["auto_escalate"] = True
        sla_escalated = True

    # Build escalation reason
    if routing["auto_escalate"]:
        reasons = []
        if (category, priority) in ROUTING_RULES and ROUTING_RULES[(category, priority)]["auto_escalate"]:
            reasons.append(f"Critical {category} incident")
        if sla_escalated:
            reasons.append(f"SLA breach risk {sla_risk:.0%}")
        escalation_reason = " + ".join(reasons) if reasons else "Policy-based escalation"
    else:
        escalation_reason = "Standard routing — no escalation required"

    # 5. Generate RAG response
    grounded_response = ""
    if run_rag:
        t0 = time.time()
        rag_result = run_rag_pipeline(subject=subject, body=body, top_k=3)
        grounded_response = rag_result.get("response", "")
        timings["rag_ms"] = round((time.time() - t0) * 1000, 1)

    timings["total_ms"] = round((time.time() - start) * 1000, 1)

    return AgentTriageResult(
        ticket_id=ticket_id,
        subject=subject,
        category=category,
        priority=priority,
        classification_confidence=clf.get("confidence", 0.0),
        classification_model=clf.get("model", ""),
        sla_breach_risk=sla_risk,
        sla_escalated=sla_escalated,
        routing_team=routing["team"],
        auto_escalate=routing["auto_escalate"],
        escalation_reason=escalation_reason,
        similar_tickets=similar,
        grounded_response=grounded_response,
        timings=timings,
        total_ms=timings["total_ms"],
    )


def _extract_sla_features(subject: str, body: str) -> dict:
    """Extract all 17 structured features from text for SLA breach prediction."""
    import re
    from datetime import datetime

    text = f"{subject} {body}"
    now = datetime.now()

    return {
        "text_length": len(text),
        "word_count": len(text.split()),
        "subject_length": len(subject),
        "code_block_count": text.count("```"),
        "url_count": len(re.findall(r'https?://', text)),
        "question_mark_count": text.count("?"),
        "exclamation_count": text.count("!"),
        "caps_word_count": sum(1 for w in text.split() if w.isupper() and len(w) > 1),
        "hour_of_day": now.hour,
        "day_of_week": now.weekday(),
        "is_weekend": int(now.weekday() >= 5),
        "is_after_hours": int(now.hour < 9 or now.hour > 18),
        "ticket_age_hours": 0,
        "reopen_count": 0,
        "comment_count": 0,
        "customer_tier_encoded": 1,
        "source_encoded": 0,
    }
