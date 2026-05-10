"""
Test the SupportPulse FastAPI endpoints.
Run this AFTER the server is up (uvicorn app.main:app --reload).
Tests: /health, /classify, /triage (fast mode, no RAG).
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def divider(title=""):
    print(f"\n{'=' * 60}")
    if title:
        print(f"  {title}")
        print("=" * 60)


def test_health():
    divider("1. Health Check")
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    print(f"  Status         : {data['status']}")
    print(f"  LLM Model      : {data['llm_model']}")
    print(f"  Fallback Model : {data['fallback_model']}")
    print(f"  Embed Model    : {data['embed_model']}")
    print(f"  Vector Index   : {data['vector_index_size']:,} tickets")
    print(f"  PASS")


def test_classify():
    divider("2. /classify — Fast Classification (no RAG)")
    payload = {
        "subject": "TLS certificate expires in 48 hours",
        "body": "Our production SSL cert auto-renewal failed. Expires in 2 days."
    }
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/classify", json=payload, timeout=30)
    total = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"  Category   : {data['category']}")
    print(f"  Priority   : {data['priority']}")
    print(f"  Team       : {data['routing_team']}")
    print(f"  Confidence : {data['confidence']}")
    print(f"  Latency    : {data['latency_ms']:.0f}ms (endpoint) | {total:.0f}ms (HTTP round-trip)")
    print(f"  PASS")


def test_triage_fast():
    divider("3. /triage — Full Pipeline (run_rag=False for speed)")
    payload = {
        "ticket_id": "API-TEST-001",
        "subject": "Payment gateway returning 403 for all transactions",
        "body": "Stripe webhooks failing since 14:00 UTC. All payments blocked. Immediate fix needed.",
        "run_rag": False
    }
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/triage", json=payload, timeout=60)
    total = (time.time() - t0) * 1000
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()

    print(f"  Ticket ID      : {data['ticket_id']}")
    print(f"  Category       : {data['classification']['category']}")
    print(f"  Priority       : {data['classification']['priority']}")
    print(f"  SLA Risk       : {data['sla_prediction']['sla_risk_score']} ({data['sla_prediction']['risk_level']})")
    print(f"  Routing Team   : {data['routing_team']}")
    print(f"  Auto-Escalate  : {data['auto_escalate']}")
    print(f"  Escalation     : {data['escalation_reason']}")
    print(f"  Similar Count  : {len(data['similar_tickets'])} tickets retrieved")
    print(f"  RAG Response   : {'Yes' if data.get('grounded_response') else 'Skipped (run_rag=False)'}")
    print(f"  Total Latency  : {total:.0f}ms (HTTP round-trip)")
    print(f"  Pipeline ms    : {data['timings_ms']}")
    print(f"  PASS")


if __name__ == "__main__":
    print("\n  SupportPulse API Test Suite")
    print("  Make sure server is running: uvicorn app.main:app --reload\n")

    try:
        test_health()
        test_classify()
        test_triage_fast()
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED")
        print(f"  Swagger UI: {BASE_URL}/docs")
        print("=" * 60)
    except Exception as e:
        print(f"\n  FAILED: {e}")
        print("  Is the server running? Run: uvicorn app.main:app --reload")
