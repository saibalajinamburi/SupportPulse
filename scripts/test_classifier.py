"""Quick GPU classifier test — 3 sample tickets."""
import os
import time
import sys

from src.models.classifier import classify_ticket

tickets = [
    (
        "Server completely down - users cannot login",
        "Our production API server has been throwing 502 errors for the past 30 minutes. "
        "All users are affected. This is a critical P0 incident. Revenue is being lost every minute."
    ),
    (
        "Add dark mode to dashboard",
        "Hi team, could you please add a dark mode toggle to the main dashboard? "
        "Many users have requested this feature including myself."
    ),
    (
        "SQL injection vulnerability in login form",
        "I discovered that the login endpoint is vulnerable to SQL injection. "
        "Input like OR 1=1 bypasses authentication completely. Needs immediate patching."
    ),
]

print("=" * 60, flush=True)
print("  SupportPulse - Gemma4 Classifier Test (GPU 1 - NVIDIA)", flush=True)
print("  Watch Task Manager > GPU 1 for activity", flush=True)
print("=" * 60, flush=True)

for subject, body in tickets:
    print(f"\nTicket: {subject}", flush=True)
    t0 = time.time()
    result = classify_ticket(subject, body)
    elapsed = time.time() - t0
    print(f"  category     : {result.get('category')}", flush=True)
    print(f"  priority     : {result.get('priority')}", flush=True)
    print(f"  routing_team : {result.get('routing_team')}", flush=True)
    print(f"  confidence   : {result.get('confidence')}", flush=True)
    print(f"  latency      : {result.get('latency_ms')}ms", flush=True)
    if result.get("error"):
        print(f"  ERROR        : {result.get('error')}", flush=True)

print("\n" + "=" * 60, flush=True)
print("  Test complete.", flush=True)
print("=" * 60, flush=True)
