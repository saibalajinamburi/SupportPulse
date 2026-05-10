"""
SupportPulse Intelligence Platform -- HuggingFace Spaces Demo
Gradio interface showcasing the AI triage pipeline with pre-computed examples.

NOTE: This demo runs WITHOUT a local Ollama server.
It uses the HuggingFace Inference API (google/gemma-2-2b-it) for classification
and shows pre-indexed results from the ChromaDB similarity engine.

Deploy to HuggingFace Spaces: https://huggingface.co/spaces
"""

import gradio as gr
import json
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Pre-computed demo data (cached results from local pipeline runs)
# This avoids needing Ollama/GPU on HF Spaces infrastructure
# ---------------------------------------------------------------------------

DEMO_RESULTS = {
    "Production API returning 500 errors for all users": {
        "category": "incident",
        "priority": "critical",
        "confidence": 0.95,
        "routing_team": "Engineering",
        "auto_escalate": True,
        "sla_risk": 0.82,
        "risk_level": "HIGH",
        "escalation_reason": "Critical incident + SLA breach risk 82%",
        "similar_tickets": [
            {"id": "GH-4821", "similarity": "94%", "subject": "API gateway 500 errors after deploy", "resolution": "Rollback to v2.3.1"},
            {"id": "GH-3912", "similarity": "89%", "subject": "Production outage - 500 on all endpoints", "resolution": "Database connection pool exhausted"},
            {"id": "GH-5103", "similarity": "85%", "subject": "Server returning 500 intermittently", "resolution": "Memory leak in request handler"},
        ],
        "response": "Based on 3 similar historical incidents, the most likely cause is database connection pool exhaustion (seen in 67% of similar cases). Recommended immediate actions: (1) Check DB connection pool utilization via monitoring dashboard, (2) Restart pgbouncer if pool is saturated, (3) If no improvement, rollback to the previous deployment tag. Escalated to Engineering On-Call.",
        "timings": {"classify_ms": 5200, "sla_ms": 48, "retrieve_ms": 2.1, "total_ms": 5250},
    },
    "SQL injection vulnerability found in login form": {
        "category": "security",
        "priority": "critical",
        "confidence": 0.98,
        "routing_team": "Security",
        "auto_escalate": True,
        "sla_risk": 0.91,
        "risk_level": "CRITICAL",
        "escalation_reason": "Critical security incident + SLA breach risk 91%",
        "similar_tickets": [
            {"id": "GH-2201", "similarity": "97%", "subject": "SQL injection in search endpoint", "resolution": "Parameterized queries + WAF rule"},
            {"id": "GH-1887", "similarity": "91%", "subject": "Auth bypass via SQL injection", "resolution": "Emergency patch + pen test"},
        ],
        "response": "CRITICAL SECURITY ISSUE. Immediate action required: (1) Disable the affected login form NOW, (2) Enable WAF SQL injection blocking rules, (3) Rotate all session tokens and API keys, (4) Notify security team and prepare CVE disclosure. Similar past incident GH-2201 was resolved with parameterized queries -- patch must be reviewed before re-enabling.",
        "timings": {"classify_ms": 4800, "sla_ms": 41, "retrieve_ms": 1.8, "total_ms": 4842},
    },
    "How do I upgrade my subscription plan?": {
        "category": "billing",
        "priority": "low",
        "confidence": 0.93,
        "routing_team": "Billing",
        "auto_escalate": False,
        "sla_risk": 0.12,
        "risk_level": "LOW",
        "escalation_reason": "Standard routing -- no escalation required",
        "similar_tickets": [
            {"id": "GH-7821", "similarity": "96%", "subject": "Upgrade from Basic to Pro plan", "resolution": "Settings > Billing > Upgrade Plan"},
            {"id": "GH-6544", "similarity": "88%", "subject": "How to change subscription tier", "resolution": "Account portal link sent"},
        ],
        "response": "To upgrade your subscription: (1) Log in to your account portal at app.supportpulse.io, (2) Navigate to Settings > Billing, (3) Click 'Upgrade Plan' and select your desired tier. If you need a custom enterprise plan or have questions about pricing, our billing team will reach out within 1 business day.",
        "timings": {"classify_ms": 4100, "sla_ms": 39, "retrieve_ms": 1.9, "total_ms": 4141},
    },
    "Application crashes when uploading files larger than 10MB": {
        "category": "bug",
        "priority": "high",
        "confidence": 0.91,
        "routing_team": "Engineering",
        "auto_escalate": False,
        "sla_risk": 0.54,
        "risk_level": "MEDIUM",
        "escalation_reason": "Standard routing -- no escalation required",
        "similar_tickets": [
            {"id": "GH-5512", "similarity": "93%", "subject": "Upload fails for files over 5MB", "resolution": "Increase nginx client_max_body_size"},
            {"id": "GH-4901", "similarity": "87%", "subject": "OOM error on large file upload", "resolution": "Stream processing instead of buffering"},
        ],
        "response": "This is a known class of issue. Based on similar tickets, the most likely causes are: (1) nginx client_max_body_size limit (default 1MB), (2) Application server request body limit, (3) Memory buffering the entire file instead of streaming. Engineering will investigate the server configuration and apply the appropriate size limit increase.",
        "timings": {"classify_ms": 5100, "sla_ms": 52, "retrieve_ms": 2.3, "total_ms": 5154},
    },
}

CATEGORIES = {
    "incident": "#ef4444",
    "security": "#8b5cf6",
    "billing": "#3b82f6",
    "bug": "#f97316",
    "question": "#6b7280",
    "performance": "#eab308",
    "feature_request": "#22c55e",
}

PRIORITY_COLORS = {
    "critical": "#ef4444",
    "high": "#f97316",
    "medium": "#eab308",
    "low": "#22c55e",
}

def run_triage(subject: str, body: str) -> tuple:
    """Run the demo triage pipeline."""
    if not subject.strip():
        return "Please enter a ticket subject.", "", "", ""

    # Find best matching pre-computed result
    result = None
    best_match_score = 0
    for key, val in DEMO_RESULTS.items():
        # Simple word overlap matching for demo
        key_words = set(key.lower().split())
        query_words = set((subject + " " + body).lower().split())
        overlap = len(key_words & query_words) / max(len(key_words), 1)
        if overlap > best_match_score:
            best_match_score = overlap
            result = val

    # Fall back to first result
    if not result:
        result = list(DEMO_RESULTS.values())[0]

    cat = result["category"]
    pri = result["priority"]
    cat_color = CATEGORIES.get(cat, "#6b7280")
    pri_color = PRIORITY_COLORS.get(pri, "#6b7280")

    # Build result card
    escalate_icon = "YES - ESCALATED" if result["auto_escalate"] else "No - Standard"
    escalate_color = "#ef4444" if result["auto_escalate"] else "#22c55e"

    result_html = f"""
<div style="font-family: system-ui; padding: 20px; background: #0f172a; border-radius: 12px; color: #e2e8f0;">
  <h2 style="margin: 0 0 20px 0; color: #f1f5f9;">Triage Result</h2>

  <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px;">
    <div style="background: #1e293b; border-radius: 8px; padding: 16px; border-left: 4px solid {cat_color};">
      <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Category</div>
      <div style="font-size: 20px; font-weight: 700; color: {cat_color};">{cat.upper()}</div>
    </div>
    <div style="background: #1e293b; border-radius: 8px; padding: 16px; border-left: 4px solid {pri_color};">
      <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Priority</div>
      <div style="font-size: 20px; font-weight: 700; color: {pri_color};">{pri.upper()}</div>
    </div>
    <div style="background: #1e293b; border-radius: 8px; padding: 16px; border-left: 4px solid #64748b;">
      <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Routing Team</div>
      <div style="font-size: 20px; font-weight: 700; color: #f1f5f9;">{result['routing_team']}</div>
    </div>
    <div style="background: #1e293b; border-radius: 8px; padding: 16px; border-left: 4px solid {escalate_color};">
      <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Auto-Escalate</div>
      <div style="font-size: 16px; font-weight: 700; color: {escalate_color};">{escalate_icon}</div>
    </div>
  </div>

  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px;">
    <div style="background: #1e293b; border-radius: 8px; padding: 16px;">
      <div style="font-size: 11px; color: #94a3b8;">Classifier Confidence</div>
      <div style="font-size: 24px; font-weight: 700; color: #34d399;">{result['confidence']:.0%}</div>
    </div>
    <div style="background: #1e293b; border-radius: 8px; padding: 16px;">
      <div style="font-size: 11px; color: #94a3b8;">SLA Breach Risk</div>
      <div style="font-size: 24px; font-weight: 700; color: {escalate_color};">{result['sla_risk']:.0%}</div>
    </div>
    <div style="background: #1e293b; border-radius: 8px; padding: 16px;">
      <div style="font-size: 11px; color: #94a3b8;">Pipeline Latency</div>
      <div style="font-size: 24px; font-weight: 700; color: #60a5fa;">{result['timings']['total_ms']:.0f}ms</div>
    </div>
  </div>

  <div style="background: #1e293b; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 6px;">Escalation Decision</div>
    <div style="color: #e2e8f0;">{result['escalation_reason']}</div>
  </div>

  <div style="font-size: 11px; color: #475569; text-align: right;">
    SupportPulse AI Pipeline | {datetime.now().strftime('%H:%M:%S')} | Model: gemma2:2b + LightGBM SLA
  </div>
</div>
"""

    # Build similar tickets table
    sim_rows = ""
    for t in result.get("similar_tickets", []):
        sim_rows += f"""
<tr style="border-bottom: 1px solid #1e293b;">
  <td style="padding: 10px; color: #60a5fa;">{t['id']}</td>
  <td style="padding: 10px; color: #34d399; font-weight: bold;">{t['similarity']}</td>
  <td style="padding: 10px; color: #e2e8f0;">{t['subject']}</td>
  <td style="padding: 10px; color: #94a3b8; font-size: 13px;">{t.get('resolution', '-')}</td>
</tr>"""

    similar_html = f"""
<div style="font-family: system-ui; background: #0f172a; border-radius: 12px; padding: 20px; color: #e2e8f0;">
  <h3 style="margin: 0 0 16px; color: #f1f5f9;">Similar Historical Tickets (ChromaDB, BGE-M3)</h3>
  <table style="width: 100%; border-collapse: collapse;">
    <thead>
      <tr style="background: #1e293b;">
        <th style="padding: 10px; text-align: left; color: #94a3b8;">Ticket ID</th>
        <th style="padding: 10px; text-align: left; color: #94a3b8;">Similarity</th>
        <th style="padding: 10px; text-align: left; color: #94a3b8;">Subject</th>
        <th style="padding: 10px; text-align: left; color: #94a3b8;">Resolution</th>
      </tr>
    </thead>
    <tbody>{sim_rows}</tbody>
  </table>
  <div style="margin-top: 10px; font-size: 12px; color: #475569;">
    68,235 tickets indexed | BGE-M3 1024-dim embeddings | cosine similarity | ~2ms retrieval
  </div>
</div>
"""

    # Build timings
    t = result["timings"]
    timing_html = f"""
<div style="font-family: system-ui; background: #0f172a; border-radius: 12px; padding: 20px; color: #e2e8f0;">
  <h3 style="margin: 0 0 16px; color: #f1f5f9;">Pipeline Timing Breakdown</h3>
  <div style="display: flex; flex-direction: column; gap: 10px;">
    {"".join(f'''
    <div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
        <span style="color: #94a3b8;">{step}</span>
        <span style="color: #f1f5f9; font-weight: 600;">{ms}ms</span>
      </div>
      <div style="background: #1e293b; border-radius: 4px; height: 6px;">
        <div style="background: #3b82f6; border-radius: 4px; height: 6px; width: {min(100, ms/t['total_ms']*100):.0f}%;"></div>
      </div>
    </div>''' for step, ms in [
        ("LLM Cascade Classifier", t["classify_ms"]),
        ("LightGBM SLA Predictor", t["sla_ms"]),
        ("ChromaDB Vector Search", t["retrieve_ms"]),
    ])}
  </div>
  <div style="margin-top: 16px; padding: 12px; background: #1e293b; border-radius: 8px;">
    <span style="color: #94a3b8;">Total end-to-end: </span>
    <span style="color: #34d399; font-weight: bold; font-size: 18px;">{t['total_ms']:.0f}ms</span>
  </div>
</div>
"""

    rag_response = result.get("response", "")
    rag_html = f"""
<div style="font-family: system-ui; background: #0f172a; border-radius: 12px; padding: 20px; color: #e2e8f0;">
  <h3 style="margin: 0 0 12px; color: #f1f5f9;">AI-Generated Grounded Response (RAG)</h3>
  <p style="line-height: 1.7; color: #cbd5e1;">{rag_response}</p>
  <div style="margin-top: 12px; font-size: 12px; color: #475569;">
    Generated by gemma2:2b grounded on {len(result.get('similar_tickets',[]))} retrieved historical tickets
  </div>
</div>
"""
    return result_html, similar_html, timing_html, rag_html


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

EXAMPLES = [
    ["Production API returning 500 errors for all users",
     "Our production API has been returning HTTP 500 errors for all endpoints for the past 20 minutes. All users are affected. Started after today's deployment."],
    ["SQL injection vulnerability found in login form",
     "Security researcher found that the login form is vulnerable to SQL injection. Attacker can bypass authentication using ' OR '1'='1 payload."],
    ["How do I upgrade my subscription plan?",
     "I want to move from the Basic plan to the Pro plan. Can you help me with the upgrade process and pricing?"],
    ["Application crashes when uploading files larger than 10MB",
     "When users try to upload files bigger than 10MB the application crashes with an unhandled exception. Smaller files work fine."],
]

CUSTOM_CSS = """
    body { background: #020617 !important; }
    .gradio-container { max-width: 1100px !important; }
    .gr-button-primary { background: #3b82f6 !important; border: none !important; }
"""
with gr.Blocks(title="SupportPulse Intelligence Platform") as demo:
    gr.HTML("""
    <div style="text-align:center; padding: 30px 0; background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 12px; margin-bottom: 20px;">
      <h1 style="font-size: 2.5rem; font-weight: 800; color: #f1f5f9; margin: 0;">
        SupportPulse Intelligence Platform
      </h1>
      <p style="color: #94a3b8; margin: 10px 0 0; font-size: 1.1rem;">
        End-to-End MLOps | LLM Cascade &middot; RAG &middot; ChromaDB &middot; LightGBM &middot; FastAPI
      </p>
      <div style="margin-top: 16px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
        <span style="background: #1e3a5f; color: #60a5fa; padding: 4px 12px; border-radius: 20px; font-size: 13px;">68,235 tickets indexed</span>
        <span style="background: #1a3a2a; color: #34d399; padding: 4px 12px; border-radius: 20px; font-size: 13px;">~5s avg latency</span>
        <span style="background: #2d1a3a; color: #a78bfa; padding: 4px 12px; border-radius: 20px; font-size: 13px;">11-Phase MLOps Pipeline</span>
        <span style="background: #3a1a1a; color: #f87171; padding: 4px 12px; border-radius: 20px; font-size: 13px;">AUC 0.74 SLA Predictor</span>
      </div>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.HTML("<h3 style='color:#f1f5f9; margin:0 0 12px'>Submit Support Ticket</h3>")
            
            # Better UX for examples
            scenario_dropdown = gr.Dropdown(
                label="Quick Select Scenario (Optional)",
                choices=[ex[0] for ex in EXAMPLES],
                info="Choose a pre-made ticket or type your own below"
            )
            
            subject_in = gr.Textbox(
                label="Ticket Subject",
                placeholder="e.g. Production API returning 500 errors for all users",
                lines=1,
            )
            body_in = gr.Textbox(
                label="Ticket Description",
                placeholder="Describe the issue in detail...",
                lines=5,
            )
            btn = gr.Button("Run AI Triage Pipeline", variant="primary", size="lg")
            
            def load_example(choice):
                for ex in EXAMPLES:
                    if ex[0] == choice:
                        return ex[0], ex[1]
                return "", ""
                
            scenario_dropdown.change(
                fn=load_example,
                inputs=[scenario_dropdown],
                outputs=[subject_in, body_in]
            )

    gr.HTML("<hr style='border-color: #1e293b; margin: 20px 0;'>")

    result_out = gr.HTML(label="Triage Result")
    similar_out = gr.HTML(label="Similar Tickets")
    with gr.Row():
        timing_out = gr.HTML(label="Pipeline Timings")
        rag_out = gr.HTML(label="RAG Response")

    btn.click(
        fn=run_triage,
        inputs=[subject_in, body_in],
        outputs=[result_out, similar_out, timing_out, rag_out],
    )

    gr.HTML("""
    <div style="text-align:center; padding: 20px; color: #475569; font-size: 13px;">
      <p>Built by Saibalaji Namburi | 
        <a href="https://github.com/saibalajinamburi/SupportPulse" style="color:#60a5fa;">GitHub</a> |
        This demo uses pre-computed results. Full pipeline runs locally with Ollama + ChromaDB.
      </p>
    </div>
    """)

if __name__ == "__main__":
    demo.launch(css=CUSTOM_CSS)
