import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

TEMPLATES = {
    "security": [
        "I noticed a potential XSS vulnerability in the {component} module. When I input {script}, it executes in the browser.",
        "My account {account_id} has unauthorized logins from IP {ip_address}. Please secure my account immediately.",
        "The {component} API endpoint is leaking PII data without authentication. This is a critical GDPR violation.",
        "I found a hardcoded API key in the open-source repository for {component}. It needs to be revoked.",
        "There is an SQL injection vulnerability in the search bar of {component}. Payload used: {script}"
    ],
    "billing": [
        "I was charged {amount} twice on my credit card ending in {cc_last4}. Please refund one of the charges.",
        "My invoice for account {account_id} shows an incorrect total. It should be {amount} but says {wrong_amount}.",
        "I want to cancel my subscription. Why am I still being charged {amount} every month?",
        "Please update my billing address for account {account_id}. The new address is {address}.",
        "My payment failed with error code {error_code}. The card ending in {cc_last4} has sufficient funds."
    ],
    "sla_breach": [
        "I opened this ticket 5 days ago and haven't received a response. This is unacceptable.",
        "My critical system is down. It's been 24 hours. Why is no one responding to account {account_id}?",
        "We have an enterprise SLA and this P0 issue in {component} has been open for 4 hours without acknowledgement.",
        "Hello? Is anyone there? I've been waiting for a week to get a simple question answered about {component}.",
        "I'm escalating this to my account manager. Ticket {ticket_id} has breached the 2-hour response SLA."
    ],
    "incident": [
        "The main application is completely down. We are getting a 502 Bad Gateway error on {component}.",
        "All our users are unable to log in. The SSO integration with {component} is failing.",
        "Production deployment failed and now the site is throwing 500 errors. Rollback is not working.",
        "We are seeing a massive spike in latency on the {component} service. Requests taking > 10 seconds.",
        "Database connection dropped. None of our microservices can connect to {component}."
    ]
}

def generate_synthetic(category: str, n: int) -> list:
    tickets = []
    now = datetime.now()
    
    for i in range(n):
        template = random.choice(TEMPLATES[category])
        
        # Fill placeholders
        body = template.format(
            component=random.choice(["auth", "checkout", "dashboard", "api", "database", "ui"]),
            script="<script>alert(1)</script>",
            account_id=f"ACC-{random.randint(10000, 99999)}",
            ip_address=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            amount=f"${random.randint(10, 500)}.00",
            wrong_amount=f"${random.randint(501, 1000)}.00",
            cc_last4=f"{random.randint(1000, 9999)}",
            address="123 Fake St, Springfield",
            error_code=random.choice(["ERR_502", "ERR_INSUFFICIENT_FUNDS", "ERR_DECLINED"]),
            ticket_id=f"TKT-{random.randint(100000, 999999)}"
        )
        
        # Create ticket
        ticket = {
            "ticket_id": f"SYN-{uuid.uuid4().hex[:8]}",
            "source": "synthetic",
            "created_at": (now - timedelta(days=random.randint(0, 365))).isoformat(),
            "subject": f"{category.capitalize()} Issue - {body[:30]}...",
            "body": body,
            "comments": [],
            "labels_raw": [category],
            "category": category,
            "priority": "high" if category in ["security", "incident"] else "medium",
            "routing_team": "security" if category == "security" else "billing" if category == "billing" else "support",
            "customer_tier": random.choice(["free", "pro", "enterprise"])
        }
        tickets.append(ticket)
        
    return tickets

def main():
    print("Generating synthetic tickets...")
    output_dir = Path("data/bronze/synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_tickets = []
    
    # Generate based on the plan
    counts = {
        "security": 2000,
        "billing": 2000,
        "sla_breach": 1500,
        "incident": 1500
    }
    
    for cat, count in counts.items():
        print(f"Generating {count} tickets for {cat}...")
        tickets = generate_synthetic(cat, count)
        all_tickets.extend(tickets)
        
    output_file = output_dir / "synthetic_tickets.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_tickets, f, indent=2)
        
    print(f"\nSaved {len(all_tickets)} synthetic tickets to {output_file}")

if __name__ == "__main__":
    main()
