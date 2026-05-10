"""RAG prompt builder — constructs grounded prompts from retrieved context."""

SYSTEM_PROMPT = """You are SupportPulse, an expert AI assistant for enterprise customer support.
You are given historical similar tickets as context. Use ONLY the provided context to answer.
If the context does not contain enough information, say so clearly. Never hallucinate solutions.
Be concise, specific, and actionable."""

RAG_TEMPLATE = """HISTORICAL SIMILAR TICKETS (use these as context):
{context}

---
NEW TICKET TO TRIAGE:
Category: {category}
Priority: {priority}
Subject: {subject}
Description: {body}

Based on the similar historical tickets above, provide:
1. IMMEDIATE ACTION: What should the support agent do first?
2. LIKELY CAUSE: Based on historical patterns, what is the most probable root cause?
3. SUGGESTED RESOLUTION: Step-by-step resolution based on how similar tickets were handled.
4. ESCALATION: Should this be escalated? To which team?

Be specific and reference the historical tickets where relevant."""


def format_context(retrieved_tickets: list[dict]) -> str:
    """Format retrieved tickets into a structured context block."""
    if not retrieved_tickets:
        return "No similar historical tickets found."

    lines = []
    for i, ticket in enumerate(retrieved_tickets, 1):
        similarity_pct = int(ticket.get("similarity", 0) * 100)
        lines.append(
            f"[Ticket {i} | Similarity: {similarity_pct}% | "
            f"Category: {ticket.get('category','')} | "
            f"Priority: {ticket.get('priority','')}]\n"
            f"Subject: {ticket.get('subject','')}"
        )

    return "\n\n".join(lines)


def build_rag_prompt(
    subject: str,
    body: str,
    category: str,
    priority: str,
    retrieved_tickets: list[dict],
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the RAG generation call."""
    context = format_context(retrieved_tickets)
    user_prompt = RAG_TEMPLATE.format(
        context=context,
        category=category,
        priority=priority,
        subject=subject[:300],
        body=body[:500],
    )
    return SYSTEM_PROMPT, user_prompt
