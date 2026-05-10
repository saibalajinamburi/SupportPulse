"""LLM Cascade Ticket Classifier — fast primary model with smart fallback."""

import json
import os
import re
import time
from typing import Optional

# Force Ollama to use the NVIDIA GPU (GPU 1), not Intel Iris Xe (GPU 0)
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Within CUDA, device 0 = first CUDA-capable GPU = NVIDIA
os.environ["OLLAMA_NUM_GPU"] = "99"       # Tell Ollama to offload all layers to GPU

import ollama
from app.config import settings

SYSTEM_PROMPT = """You are a strict support ticket classifier for an enterprise MLOps platform.
You must classify tickets into EXACTLY the provided categories with NO deviation.
Always respond with valid JSON only. No explanation. No markdown. Just JSON."""

CLASSIFICATION_PROMPT = """Classify this support ticket into exactly one category, one priority, and one routing team.

VALID CATEGORIES: bug, feature, security, billing, performance, docs, question, incident, sla_breach, ui, test, dependency
VALID PRIORITIES: critical, high, medium, low
VALID ROUTING TEAMS: engineering, security, billing, infra, support

Ticket Subject: {subject}
Ticket Body: {body}

Respond with ONLY this JSON, no other text:
{{
  "category": "<one of the valid categories>",
  "priority": "<one of the valid priorities>",
  "routing_team": "<one of the valid routing teams>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence max>"
}}"""

VALID_CATEGORIES = {
    "bug", "feature", "security", "billing", "performance",
    "docs", "question", "incident", "sla_breach", "ui", "test", "dependency"
}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_ROUTING_TEAMS = {"engineering", "security", "billing", "infra", "support"}

FALLBACK_RESULT = {
    "category": "question",
    "priority": "medium",
    "routing_team": "support",
    "confidence": 0.0,
    "reasoning": "Classification failed — fallback applied."
}


def _extract_json(text: str) -> Optional[dict]:
    """Extract and parse first JSON object from model output."""
    match = re.search(r'\{[\s\S]*?\}', text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _validate_and_fix(result: dict) -> dict:
    """Ensure all fields are valid, apply fallbacks for invalid values."""
    result["category"] = result.get("category", "question").lower().strip()
    result["priority"] = result.get("priority", "medium").lower().strip()
    result["routing_team"] = result.get("routing_team", "support").lower().strip()

    if result["category"] not in VALID_CATEGORIES:
        result["category"] = "question"
        result["confidence"] = 0.0

    if result["priority"] not in VALID_PRIORITIES:
        result["priority"] = "medium"

    if result["routing_team"] not in VALID_ROUTING_TEAMS:
        result["routing_team"] = "support"

    result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
    return result


def classify_ticket(
    subject: str,
    body: str,
    model: str = None,
    fallback_model: str = None,
    timeout: int = 60
) -> dict:
    """Classify ticket using LLM Cascade (fast model first, heavy model if uncertain)."""
    primary_model = model or settings.OLLAMA_LLM_MODEL
    
    # 1. Try Primary Model (Fast)
    result = _run_ollama(subject, body, primary_model)
    
    # 2. Evaluate if we need to Escalate (Cascade)
    needs_escalation = (
        fallback_model is not None 
        and (result.get("error") or result.get("confidence", 0.0) < 0.75)
    )
    
    if needs_escalation:
        fallback_result = _run_ollama(subject, body, fallback_model)
        # Only override if fallback actually succeeded or primary had an error
        if not fallback_result.get("error") or result.get("error"):
            fallback_result["escalated"] = True
            fallback_result["primary_model"] = primary_model
            return fallback_result
            
    result["escalated"] = False
    return result


def _run_ollama(subject: str, body: str, model_name: str) -> dict:
    """Internal helper to run Ollama generation."""
    prompt = CLASSIFICATION_PROMPT.format(
        subject=subject[:500],
        body=body[:2000]
    )

    start = time.time()
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.1,
                "num_predict": 256,
                "num_gpu": 99,
            }
        )
        raw_text = response["message"]["content"]
        elapsed = time.time() - start

        parsed = _extract_json(raw_text)
        if parsed is None:
            result = FALLBACK_RESULT.copy()
            result["error"] = "JSON parse failed"
        else:
            result = _validate_and_fix(parsed)

        result["latency_ms"] = round(elapsed * 1000, 1)
        result["model"] = model_name
        return result

    except Exception as e:
        fallback = FALLBACK_RESULT.copy()
        fallback["error"] = str(e)
        fallback["latency_ms"] = round((time.time() - start) * 1000, 1)
        fallback["model"] = model_name
        return fallback


def classify_batch(
    tickets: list[dict],
    model: str = None,
    fallback_model: str = None,
    use_cascade: bool = True,
    show_progress: bool = True
) -> list[dict]:
    """Classify tickets using the LLM Cascade pattern with ETA progress."""
    results = []
    total = len(tickets)
    start_time = time.time()
    escalated_count = 0

    # Auto-resolve models from settings if not provided
    primary = model or settings.OLLAMA_LLM_MODEL
    fallback = fallback_model or (settings.OLLAMA_FALLBACK_MODEL if use_cascade else None)

    for i, ticket in enumerate(tickets):
        result = classify_ticket(
            subject=ticket.get("subject", ""),
            body=ticket.get("body", ""),
            model=primary,
            fallback_model=fallback
        )
        result["ticket_id"] = ticket.get("ticket_id", "")
        results.append(result)

        if result.get("escalated"):
            escalated_count += 1

        if show_progress and (i + 1) % 5 == 0:
            import datetime
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 1
            remaining = (total - (i + 1)) / rate if rate > 0 else 0
            pct = ((i + 1) / total) * 100
            eta = str(datetime.timedelta(seconds=int(remaining)))
            avg_ms = (elapsed / (i + 1)) * 1000
            print(
                f"  [Cascade] {pct:5.1f}% | {i+1}/{total}"
                f" | avg={avg_ms:.0f}ms | escalated={escalated_count} | ETA={eta}  ",
                end="\r", flush=True
            )

    if show_progress:
        total_time = time.time() - start_time
        esc_pct = (escalated_count / total) * 100 if total > 0 else 0
        print(
            f"  [Cascade] Done | {total}/{total} in {total_time:.1f}s"
            f" | {escalated_count} escalated ({esc_pct:.1f}% hit fallback)"
        )

    return results
