"""Test the LLM Cascade (fast 2b primary + smart 4b fallback)."""
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.models.classifier import classify_ticket, classify_batch
from app.config import settings

tickets = [
    {
        "ticket_id": "T001",
        "subject": "Server completely down - users cannot login",
        "body": "Our production API server has been throwing 502 errors for 30 minutes. All users affected. Revenue being lost every minute."
    },
    {
        "ticket_id": "T002",
        "subject": "Add dark mode to dashboard",
        "body": "Could you please add a dark mode toggle? Many users have requested this."
    },
    {
        "ticket_id": "T003",
        "subject": "SQL injection vulnerability in login form",
        "body": "The login endpoint is vulnerable to SQL injection. OR 1=1 bypasses authentication. Needs immediate patching."
    },
    {
        "ticket_id": "T004",
        "subject": "Billing charge incorrect",
        "body": "We were charged $2,400 this month but our plan is $800/month. Please refund and fix the billing system."
    },
    {
        "ticket_id": "T005",
        "subject": "API latency increased 300%",
        "body": "Since yesterday's deployment our API response times went from 50ms to 200ms. All regions affected."
    },
]

print("=" * 65)
print("  SupportPulse - LLM Cascade Test")
print(f"  Primary  : {settings.OLLAMA_LLM_MODEL} (fast, fits in VRAM)")
print(f"  Fallback : {settings.OLLAMA_FALLBACK_MODEL} (smart, used only when needed)")
print("=" * 65)

results = classify_batch(tickets, show_progress=True)

print()
print(f"  {'ID':<6} {'Category':<12} {'Priority':<10} {'Routing':<12} {'Conf':<6} {'Escalated':<10} {'Model'}")
print(f"  {'-'*6} {'-'*12} {'-'*10} {'-'*12} {'-'*6} {'-'*10} {'-'*15}")
for r in results:
    model_tag = r.get("model", "").replace("gemma4:e4b", "FALLBACK").replace("gemma2:2b", "fast")
    print(
        f"  {r.get('ticket_id',''):<6} "
        f"{r.get('category',''):<12} "
        f"{r.get('priority',''):<10} "
        f"{r.get('routing_team',''):<12} "
        f"{r.get('confidence', 0):<6.2f} "
        f"{'YES' if r.get('escalated') else 'no':<10} "
        f"{model_tag}"
    )
    if r.get("error"):
        print(f"         ERROR: {r.get('error')}")

print("=" * 65)
