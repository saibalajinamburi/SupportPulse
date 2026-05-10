"""SupportPulse Ticket Triage API — production-grade FastAPI server."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.schemas import (
    TicketRequest, TriageResponse, ClassifyRequest,
    ClassifyResponse, HealthResponse,
    ClassificationResult, SLAResult, SimilarTicket
)
from src.agent.triage_agent import triage
from src.models.classifier import classify_ticket
from src.models.sla_model import predict_sla_risk
from src.vector.indexer import load_index
from src.vector.retriever import embed_text
from src.monitoring.request_logger import log_triage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup & shutdown lifecycle manager.
    Pre-warms all models on startup so the FIRST user request is fast.
    Without this, the first /triage call would take 44+ seconds (cold start).
    """
    print("[Startup] Pre-warming BGE-M3 embedding model...", flush=True)
    try:
        embed_text("warmup ping")
        print("[Startup] BGE-M3 warm.", flush=True)
    except Exception as e:
        print(f"[Startup] WARNING: BGE-M3 warmup failed: {e}", flush=True)

    print("[Startup] Loading ChromaDB vector index...", flush=True)
    try:
        col = load_index()
        app.state.vector_count = col.count()
        print(f"[Startup] ChromaDB loaded: {app.state.vector_count:,} vectors.", flush=True)
    except Exception as e:
        app.state.vector_count = 0
        print(f"[Startup] WARNING: ChromaDB load failed: {e}", flush=True)

    print("[Startup] SupportPulse API ready.", flush=True)
    yield
    print("[Shutdown] SupportPulse API shutting down.", flush=True)


app = FastAPI(
    title="SupportPulse Intelligence API",
    description=(
        "Production-grade support ticket triage using LLM Cascade classification, "
        "LightGBM SLA prediction, ChromaDB vector search, and RAG response generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Instrument the app to expose /metrics for Prometheus
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Check API health and model availability."""
    return HealthResponse(
        status="healthy",
        llm_model=settings.OLLAMA_LLM_MODEL,
        fallback_model=settings.OLLAMA_FALLBACK_MODEL,
        embed_model=settings.OLLAMA_EMBED_MODEL,
        vector_index_size=getattr(app.state, "vector_count", 0),
        message="All systems operational"
    )


@app.post("/triage", response_model=TriageResponse, tags=["Triage"])
def triage_ticket(request: TicketRequest):
    """
    Full triage pipeline: classify → SLA predict → retrieve → route → [RAG generate].
    Set run_rag=False for 2x faster routing-only mode.
    """
    result = triage(
        subject=request.subject,
        body=request.body,
        ticket_id=request.ticket_id,
        run_rag=request.run_rag,
    )

    sla_result = predict_sla_risk({
        "text_length": len(request.body),
        "word_count": len(request.body.split()),
        "subject_length": len(request.subject),
        "code_block_count": request.body.count("```"),
        "url_count": request.body.count("http"),
        "question_mark_count": request.body.count("?"),
        "exclamation_count": request.body.count("!"),
        "caps_word_count": sum(1 for w in request.body.split() if w.isupper() and len(w) > 1),
        "hour_of_day": time.localtime().tm_hour,
        "day_of_week": time.localtime().tm_wday,
        "is_weekend": int(time.localtime().tm_wday >= 5),
        "is_after_hours": int(time.localtime().tm_hour < 9 or time.localtime().tm_hour > 18),
        "ticket_age_hours": 0, "reopen_count": 0, "comment_count": 0,
        "customer_tier_encoded": 1, "source_encoded": 0,
    })

    response = TriageResponse(
        ticket_id=result.ticket_id,
        subject=result.subject,
        classification=ClassificationResult(
            category=result.category,
            priority=result.priority,
            routing_team=result.routing_team,
            confidence=result.classification_confidence,
            model=result.classification_model,
            escalated=result.auto_escalate,
        ),
        sla_prediction=SLAResult(**sla_result),
        routing_team=result.routing_team,
        auto_escalate=result.auto_escalate,
        escalation_reason=result.escalation_reason,
        similar_tickets=[SimilarTicket(**t) for t in result.similar_tickets],
        grounded_response=result.grounded_response or None,
        timings_ms=result.timings,
        total_ms=result.total_ms,
    )

    # Persist to observability log (async-safe: SQLite write is fast)
    try:
        log_triage(
            ticket_id=result.ticket_id,
            subject=request.subject,
            category=result.category,
            priority=result.priority,
            routing_team=result.routing_team,
            auto_escalate=result.auto_escalate,
            sla_risk=sla_result["sla_risk_score"],
            confidence=result.classification_confidence,
            timings=result.timings,
            run_rag=request.run_rag,
        )
    except Exception:
        pass  # Never let logging break the response

    return response


@app.post("/classify", response_model=ClassifyResponse, tags=["Triage"])
def classify_only(request: ClassifyRequest):
    """
    Fast classification endpoint — LLM Cascade only, no retrieval or RAG.
    Typical latency: 1-5 seconds.
    """
    t0 = time.time()
    result = classify_ticket(
        subject=request.subject,
        body=request.body,
        model=settings.OLLAMA_LLM_MODEL,
        fallback_model=settings.OLLAMA_FALLBACK_MODEL,
    )
    latency = (time.time() - t0) * 1000

    if result.get("error") and not result.get("category"):
        raise HTTPException(status_code=503, detail="Classifier unavailable")

    return ClassifyResponse(
        category=result.get("category", "question"),
        priority=result.get("priority", "medium"),
        routing_team=result.get("routing_team", "support"),
        confidence=result.get("confidence", 0.0),
        model=result.get("model", settings.OLLAMA_LLM_MODEL),
        latency_ms=round(latency, 1),
    )
