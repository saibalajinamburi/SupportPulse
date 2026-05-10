"""
Evaluate Agent routing accuracy on 20 labeled tickets.
Runs WITHOUT RAG generation (run_rag=False) for speed — purely tests
classification + SLA + routing logic. Completes in ~30 seconds.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.agent.triage_agent import triage

# 20 hand-labeled tickets with ground-truth routing + escalation expectations
# Covers all major categories and priority combinations
TEST_CASES = [
    # (subject, body, expected_team, expected_auto_escalate)
    ("Production API returning 500 errors for all users",
     "All API endpoints down. 100% error rate for 15 minutes. Revenue impact.",
     "engineering", True),

    ("SQL injection in admin login endpoint",
     "Attacker can bypass auth using ' OR 1=1 --. Needs immediate patch.",
     "security", True),

    ("Invoice charged in wrong currency USD vs EUR",
     "Customer billed USD but contract says EUR. 15% overcharge.",
     "billing", False),

    ("Dashboard page takes 30 seconds to load",
     "Analytics dashboard timing out for enterprise customers.",
     "infra", False),

    ("How to export data to CSV?",
     "Hi, I need to know how to export my ticket data to CSV format.",
     "support", False),

    ("Memory leak in backend service causing OOM crashes",
     "Backend pod restarting every 2 hours. Memory usage grows to 8GB then crashes.",
     "engineering", False),

    ("Unauthorized access attempt detected from 192.168.1.100",
     "Multiple failed login attempts detected. Possible brute force attack.",
     "security", True),

    ("Subscription auto-renewed without consent",
     "Customer said they cancelled last month but were charged again.",
     "billing", False),

    ("Database CPU at 100% — entire platform degraded",
     "Primary DB CPU pegged at 100%. All queries timing out. All tenants affected.",
     "engineering", True),

    ("Add bulk ticket export feature",
     "Would like the ability to export 1000+ tickets at once via API.",
     "support", False),

    ("TLS certificate expiring in 3 days",
     "SSL cert for api.example.com expires in 72 hours. Auto-renewal failed.",
     "security", True),

    ("Wrong tax calculation on enterprise invoice",
     "EU customer charged US tax rate. Compliance issue.",
     "billing", False),

    ("Kafka consumer lag growing — event processing delayed by 2 hours",
     "Consumer group stuck. Messages in queue but not being processed.",
     "infra", False),

    ("Where can I find API documentation?",
     "Looking for REST API docs and authentication examples.",
     "support", False),

    ("Gemma model inference crashes on RTX 3090",
     "GPU OOM error when running with batch_size > 4.",
     "engineering", False),

    ("Critical: Payment gateway integration returning 403",
     "Stripe webhooks not reaching our endpoint. Payments failing for all users.",
     "engineering", True),

    ("Can we get volume discount pricing?",
     "We have 500 users and want to negotiate enterprise pricing.",
     "billing", False),

    ("Disk I/O saturation on primary database node",
     "Disk write latency spiked from 2ms to 800ms after last nights migration.",
     "infra", False),

    ("OAuth2 token refresh failing after 1 hour",
     "Users getting logged out every hour. Access tokens not being refreshed.",
     "engineering", False),

    ("Need to update company billing address",
     "We moved offices. Need to update the billing address on the account.",
     "billing", False),
]


def evaluate_routing():
    print("=" * 65)
    print("  SupportPulse Phase 6 — Agent Routing Evaluation")
    print("  Mode: No RAG generation (pure routing logic test)")
    print(f"  Sample: {len(TEST_CASES)} labeled tickets")
    print("=" * 65)

    correct_team = 0
    correct_escalation = 0
    results = []

    for i, (subject, body, exp_team, exp_escalate) in enumerate(TEST_CASES, 1):
        result = triage(subject=subject, body=body, ticket_id=f"T{i:03d}", run_rag=False)

        team_ok = result.routing_team == exp_team
        esc_ok = result.auto_escalate == exp_escalate

        if team_ok:
            correct_team += 1
        if esc_ok:
            correct_escalation += 1

        results.append({
            "id": f"T{i:03d}",
            "category": result.category,
            "priority": result.priority,
            "sla_risk": result.sla_breach_risk,
            "pred_team": result.routing_team,
            "exp_team": exp_team,
            "team_ok": team_ok,
            "pred_esc": result.auto_escalate,
            "exp_esc": exp_escalate,
            "esc_ok": esc_ok,
            "total_ms": result.total_ms,
        })

        status = "OK " if (team_ok and esc_ok) else "ERR"
        print(
            f"  [{status}] T{i:03d} | {result.category:<12} {result.priority:<8}"
            f" | Team: {result.routing_team:<12} (exp:{exp_team:<12})"
            f" | Esc: {str(result.auto_escalate):<5} (exp:{str(exp_escalate):<5})"
            f" | SLA:{result.sla_breach_risk:.2f}"
        )

    n = len(TEST_CASES)
    team_acc = correct_team / n
    esc_acc = correct_escalation / n
    both_acc = sum(1 for r in results if r["team_ok"] and r["esc_ok"]) / n
    avg_ms = sum(r["total_ms"] for r in results) / n

    print("\n" + "=" * 65)
    print("  AGENT EVALUATION RESULTS")
    print("=" * 65)
    print(f"  Team Routing Accuracy  : {team_acc:.1%} ({correct_team}/{n})")
    print(f"  Escalation Accuracy    : {esc_acc:.1%} ({correct_escalation}/{n})")
    print(f"  Full Match (both)      : {both_acc:.1%}")
    print(f"  Avg Latency (no RAG)   : {avg_ms:.0f}ms per ticket")
    print("=" * 65)

    return {"team_accuracy": team_acc, "escalation_accuracy": esc_acc, "full_match": both_acc}


if __name__ == "__main__":
    evaluate_routing()
