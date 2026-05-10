"""
SupportPulse Dashboard — Streamlit monitoring and live triage UI.
Run with: streamlit run dashboard/streamlit_app.py
Requires: pip install streamlit pandas requests
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import requests
import time

from src.monitoring.request_logger import get_recent, get_stats

API_BASE = "http://localhost:8000"

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SupportPulse Intelligence Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
[data-testid="stSidebar"] { background: #0e1117; }
.stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 SupportPulse")
    st.caption("AI-Powered Ticket Triage")
    st.divider()

    page = st.radio(
        "Navigate",
        ["🎯 Live Triage", "📊 Analytics", "🔍 Request Log", "💚 System Health"],
    )
    st.divider()

    # Quick API health check in sidebar
    try:
        health_resp = requests.get(f"{API_BASE}/health", timeout=3)
        health_resp.raise_for_status()
        h = health_resp.json()
        st.success("✅ API: Online")
        st.caption(f"📦 {h.get('vector_index_size', 0):,} tickets indexed")
        st.caption(f"🤖 {h.get('llm_model', 'N/A')} & {h.get('fallback_model', 'N/A')}")
    except Exception:
        st.error("❌ API: Offline")
        st.caption("Run: uvicorn app.main:app --port 8000")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1: Live Triage
# ─────────────────────────────────────────────────────────────────────────────
if "🎯" in page:
    st.title("🎯 Live Ticket Triage")
    st.caption("Submit a support ticket and see the full AI pipeline run in real-time.")

    EXAMPLES = {
        "Custom...": {"subject": "", "body": ""},
        "Production Outage": {"subject": "Production API returning 500 errors for all users", "body": "Our production API has been returning HTTP 500 errors for all endpoints for the past 20 minutes. All users are affected. Started after today's deployment."},
        "SQL Injection": {"subject": "SQL injection vulnerability found in login form", "body": "Security researcher found that the login form is vulnerable to SQL injection. Attacker can bypass authentication using ' OR '1'='1 payload."},
        "Upgrade Plan": {"subject": "How do I upgrade my subscription plan?", "body": "I want to move from the Basic plan to the Pro plan. Can you help me with the upgrade process and pricing?"},
        "File Upload Crash": {"subject": "Application crashes when uploading files larger than 10MB", "body": "When users try to upload files bigger than 10MB the application crashes with an unhandled exception. Smaller files work fine."}
    }

    selected_scenario = st.selectbox("Quick Select Scenario (Optional)", list(EXAMPLES.keys()))
    default_sub = EXAMPLES[selected_scenario]["subject"]
    default_body = EXAMPLES[selected_scenario]["body"]

    with st.form("triage_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            subject = st.text_input(
                "Ticket Subject",
                value=default_sub,
                placeholder="e.g. Production API returning 500 errors for all users"
            )
        with col2:
            ticket_id = st.text_input("Ticket ID", value="LIVE-001")

        body = st.text_area(
            "Ticket Description",
            value=default_body,
            placeholder="Describe the issue in detail...",
            height=140,
        )

        run_rag = st.checkbox(
            "Generate AI Response via RAG (adds ~15s)",
            value=False,
        )
        submitted = st.form_submit_button("⚡ Run Triage", type="primary", use_container_width=True)

    if submitted:
        if not subject.strip() or not body.strip():
            st.warning("Please fill in both Subject and Description.")
        else:
            with st.spinner("Running AI triage pipeline..."):
                t0 = time.time()
                try:
                    resp = requests.post(
                        f"{API_BASE}/triage",
                        json={
                            "ticket_id": ticket_id,
                            "subject": subject,
                            "body": body,
                            "run_rag": run_rag,
                        },
                        timeout=180,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    elapsed_ms = (time.time() - t0) * 1000

                    st.divider()
                    st.subheader("📋 Triage Result")

                    # Row 1 — Classification & Routing
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Category", data["classification"]["category"].upper())
                    c2.metric("Priority", data["classification"]["priority"].upper())
                    c3.metric("Routing Team", data["routing_team"].upper())
                    escalate_label = "🔴 YES" if data["auto_escalate"] else "🟢 NO"
                    c4.metric("Auto-Escalate", escalate_label)

                    # Row 2 — Confidence, SLA, Latency
                    c5, c6, c7, c8 = st.columns(4)
                    conf = data["classification"].get("confidence", 0)
                    c5.metric("Confidence", f"{conf:.0%}")
                    sla_score = data["sla_prediction"].get("sla_risk_score", 0)
                    c6.metric("SLA Risk", f"{sla_score:.0%}")
                    c7.metric("SLA Level", data["sla_prediction"].get("risk_level", "N/A").upper())
                    c8.metric("Latency", f"{elapsed_ms:.0f}ms")

                    if data.get("auto_escalate"):
                        st.warning(f"⚠️ Escalated: {data.get('escalation_reason', '')}")

                    # Similar Tickets
                    similar = data.get("similar_tickets", [])
                    if similar:
                        st.subheader("📎 Similar Historical Tickets")
                        sim_df = pd.DataFrame(similar)
                        if "similarity" in sim_df.columns:
                            sim_df["similarity"] = sim_df["similarity"].apply(lambda x: f"{float(x):.1%}")
                        display_cols = [c for c in ["ticket_id", "similarity", "category", "priority", "subject"] if c in sim_df.columns]
                        st.dataframe(sim_df[display_cols], use_container_width=True)

                    # RAG Response
                    rag_text = data.get("grounded_response")
                    if rag_text:
                        st.subheader("🤖 AI-Generated Grounded Response")
                        st.info(rag_text)

                    # Timings breakdown
                    timings = data.get("timings_ms", {})
                    if timings:
                        with st.expander("⏱️ Pipeline Timing Breakdown"):
                            rows_t = [
                                {"Step": k.replace("_ms", "").replace("_", " ").title(), "Latency (ms)": round(v, 1)}
                                for k, v in timings.items() if k != "total_ms" and isinstance(v, (int, float))
                            ]
                            if rows_t:
                                timing_df = pd.DataFrame(rows_t).set_index("Step")
                                st.bar_chart(timing_df)

                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. Model may be loading — try again in 10 seconds.")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API. Run: `uvicorn app.main:app --port 8000`")
                except Exception as exc:
                    st.error(f"❌ Unexpected error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: Analytics
# ─────────────────────────────────────────────────────────────────────────────
elif "📊" in page:
    st.title("📊 Triage Analytics")

    try:
        stats = get_stats()
    except Exception as e:
        st.error(f"Could not load stats: {e}")
        st.stop()

    if stats["total"] == 0:
        st.info("📭 No triage requests logged yet. Submit tickets from the Live Triage page first.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Triaged", stats["total"])
        c2.metric("Auto-Escalated", stats["escalated"])
        c3.metric("Escalation Rate", f"{stats['escalation_rate']:.0%}")
        c4.metric("Avg Latency", f"{stats['avg_latency_ms']:.0f}ms")

        cat_counts = stats.get("category_counts", {})
        if cat_counts:
            st.subheader("Category Distribution")
            cat_df = pd.DataFrame(
                list(cat_counts.items()),
                columns=["Category", "Count"]
            ).sort_values("Count", ascending=False)
            st.bar_chart(cat_df.set_index("Category"))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3: Request Log
# ─────────────────────────────────────────────────────────────────────────────
elif "🔍" in page:
    st.title("🔍 Request Log")
    st.caption("Last 50 triage requests persisted by the API observability logger.")

    try:
        rows = get_recent(50)
    except Exception as e:
        st.error(f"Could not load request log: {e}")
        st.stop()

    if not rows:
        st.info("📭 No requests logged yet.")
    else:
        df = pd.DataFrame(rows)
        df["auto_escalate"] = df["auto_escalate"].map({1: "YES", 0: "no"})
        df["sla_risk"] = df["sla_risk"].apply(lambda x: f"{float(x):.0%}")
        df["confidence"] = df["confidence"].apply(lambda x: f"{float(x):.0%}")
        df["total_ms"] = df["total_ms"].apply(lambda x: f"{float(x):.0f}ms")

        display = [c for c in ["ts", "ticket_id", "category", "priority", "routing_team",
                                "auto_escalate", "sla_risk", "confidence", "total_ms"] if c in df.columns]
        st.dataframe(df[display], use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4: System Health
# ─────────────────────────────────────────────────────────────────────────────
elif "💚" in page:
    st.title("💚 System Health")

    try:
        health = requests.get(f"{API_BASE}/health", timeout=5)
        health.raise_for_status()
        h = health.json()

        st.success("✅ API Server: Online")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Models")
            st.code(
                f"Primary LLM  : {h.get('llm_model', 'N/A')}\n"
                f"Fallback LLM : {h.get('fallback_model', 'N/A')}\n"
                f"Embeddings   : {h.get('embed_model', 'N/A')}",
                language=None
            )
        with c2:
            st.subheader("Vector Index")
            st.metric("Indexed Tickets", f"{h.get('vector_index_size', 0):,}")
            st.caption("ChromaDB + BGE-M3 (cosine similarity, HNSW index)")

        st.subheader("Pipeline Architecture")
        st.code(
            "POST /triage\n"
            "  │\n"
            "  ├─ [1] LLM Cascade Classifier (gemma4:e4b primary)\n"
            "  ├─ [2] LightGBM SLA Breach Predictor\n"
            "  ├─ [3] ChromaDB Semantic Search (68,235 vectors, ~4ms)\n"
            "  ├─ [4] Deterministic Routing Rules + SLA Override\n"
            "  └─ [5] RAG Response Generator (optional, gemma4:e4b)\n"
            "\n"
            "  SQLite Observability → data/requests.db\n"
            "  Dashboard            → http://localhost:8501",
            language=None
        )
    except Exception:
        st.error("❌ API Server: Offline")
        st.code("uvicorn app.main:app --host 0.0.0.0 --port 8000", language="bash")
        st.info("Start the API server in a separate terminal, then refresh this page.")
