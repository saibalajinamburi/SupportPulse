"""Test the full RAG pipeline end-to-end on 3 curated tickets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.rag.pipeline import run_rag_pipeline

TEST_TICKETS = [
    {
        "subject": "Production database connection pool exhausted",
        "body": "All API endpoints returning 503. DB connection pool at max (100/100). Started 20 mins ago after deploy. Users cannot access the app."
    },
    {
        "subject": "Invoice shows wrong currency",
        "body": "Customer account #8842 billed in USD but their contract specifies EUR. Difference is approximately 15% due to exchange rate. They are threatening to cancel."
    },
    {
        "subject": "How to configure SSO with Okta?",
        "body": "We are trying to set up SSO with Okta for our enterprise account but the documentation seems outdated. The callback URL configuration is not working."
    },
]


def main():
    for i, ticket in enumerate(TEST_TICKETS, 1):
        print(f"\n{'=' * 65}")
        print(f"  TICKET {i}: {ticket['subject']}")
        print(f"{'=' * 65}")

        result = run_rag_pipeline(
            subject=ticket["subject"],
            body=ticket["body"],
            top_k=3
        )

        clf = result["classification"]
        timings = result["timings"]

        print(f"\n  [CLASSIFICATION]")
        print(f"  Category  : {clf.get('category')}  | Priority : {clf.get('priority')}")
        print(f"  Routing   : {clf.get('routing_team')}  | Confidence: {clf.get('confidence')}")

        print(f"\n  [RETRIEVED CONTEXT] (Top 3 similar tickets)")
        for j, t in enumerate(result["retrieved_tickets"], 1):
            print(f"  {j}. [{t['similarity']*100:.0f}% similar] {t['subject'][:70]}")
            print(f"     Category={t['category']} | Priority={t['priority']}")

        print(f"\n  [GROUNDED RESPONSE]")
        print("  " + result["response"].replace("\n", "\n  "))

        print(f"\n  [TIMINGS]")
        print(f"  Classify : {timings['classify_ms']}ms")
        print(f"  Retrieve : {timings['retrieve_ms']}ms")
        print(f"  Generate : {timings['generate_ms']}ms")
        print(f"  TOTAL    : {timings['total_ms']}ms")


if __name__ == "__main__":
    main()
