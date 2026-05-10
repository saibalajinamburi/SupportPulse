"""
Simulates realistic API traffic to populate the local observability dashboard.
Generates 100+ requests with varying categories, latencies, confidence scores,
and SLA risks so the Streamlit graphs look populated and realistic.
"""

import time
import random
import uuid
import datetime
from src.monitoring.request_logger import log_triage

CATEGORIES = ["incident", "bug", "security", "billing", "performance", "question"]
PRIORITIES = ["critical", "high", "medium", "low"]
TEAMS = ["engineering", "security", "infra", "billing", "support"]

def generate_simulated_traffic(num_requests=150):
    print(f"Simulating {num_requests} triage requests...")
    
    # We want to backdate some of these so the timeline looks interesting
    now = datetime.datetime.now(datetime.timezone.utc)
    
    success_count = 0
    for i in range(num_requests):
        # Simulate time distribution (over the last 24 hours)
        hours_ago = random.uniform(0, 24)
        sim_time = now - datetime.timedelta(hours=hours_ago)
        
        # Pick random but weighted attributes
        cat = random.choices(CATEGORIES, weights=[0.3, 0.2, 0.05, 0.15, 0.1, 0.2])[0]
        pri = random.choices(PRIORITIES, weights=[0.1, 0.2, 0.4, 0.3])[0]
        team = random.choice(TEAMS)
        
        confidence = random.uniform(0.65, 0.99)
        sla_risk = random.uniform(0.05, 0.95)
        auto_escalate = (sla_risk > 0.75) or (pri == "critical")
        
        # Simulate realistic latencies
        classify_ms = random.uniform(2000, 8000)
        sla_ms = random.uniform(10, 50)
        retrieve_ms = random.uniform(1, 10)
        rag_ms = random.uniform(4000, 12000) if random.random() > 0.5 else 0
        total_ms = classify_ms + sla_ms + retrieve_ms + rag_ms + random.uniform(10, 50)
        
        timings = {
            "classify_ms": round(classify_ms, 1),
            "sla_ms": round(sla_ms, 1),
            "retrieve_ms": round(retrieve_ms, 1),
            "rag_ms": round(rag_ms, 1),
            "total_ms": round(total_ms, 1)
        }
        
        ticket_id = f"SIM-{1000+i}"
        subject = f"Simulated ticket regarding {cat}"
        
        try:
            # We must monkeypatch datetime inside the logger to simulate past events
            import src.monitoring.request_logger as logger_module
            original_now = logger_module.datetime
            
            class MockDatetime:
                @classmethod
                def now(cls, tz=None):
                    return sim_time
                @classmethod
                def utcnow(cls):
                    # For python < 3.12 compatibility in the logger
                    return sim_time.replace(tzinfo=None)
            
            logger_module.datetime = MockDatetime
            
            log_triage(
                ticket_id=ticket_id,
                subject=subject,
                category=cat,
                priority=pri,
                routing_team=team,
                auto_escalate=bool(auto_escalate),
                sla_risk=sla_risk,
                confidence=confidence,
                timings=timings,
                run_rag=(rag_ms > 0)
            )
            
            # Restore
            logger_module.datetime = original_now
            success_count += 1
            
        except Exception as e:
            print(f"Error logging: {e}")
            
    print(f"Successfully populated {success_count} requests into the database.")
    print("Refresh your Streamlit dashboard (http://localhost:8501) to see the graphs!")

if __name__ == "__main__":
    generate_simulated_traffic()
