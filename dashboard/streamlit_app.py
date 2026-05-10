"""
SupportPulse Dashboard — Streamlit monitoring and live triage UI.
Run with: streamlit run dashboard/streamlit_app.py
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

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/technical-support.png", width=64)
    st.title("SupportPulse")
    st.caption("AI-Powered Ticket Triage")
    st.divider()
    page = st.radio(
        "Navigate",
        ["🎯 Live Triage", "📊 Analytics", "🔍 Request Log", "💚 System Health"],
        label_visibility="collapsed"
    )
    st.divider()

    # Quick API health check
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3).json()
        st.success("API: Online")
        st.caption(f"Index: {health['vector_index_size']:,} tickets")
    except Exception:
        st.error("API: Offline")
        st.caption("Start: uvicorn app.main:app")


# ── Live Triage Page ──────────────────────────────────────────────────────────
if "🎯" in page:
    st.title("🎯 Live Ticket Triage")
    st.caption("Submit a support ticket and watch the full AI pipeline run in real-time.")

    with st.form("triage_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            subject = st.text_input(
                "Ticket Subject",
                placeholder="e.g. Production API returning 500 errors for all users"
            )
        with col2:
            ticket_id = st.text_input("Ticket ID", value="LIVE-001")

        body = st.text_area(
            "Ticket Description",
            placeholder="Describe the issue in detail...",
            height=120
        )

        col_a, col_b, _ = st.columns([1, 1, 3])
        with col_a:
            run_rag = st.checkbox("Generate AI Response (RAG)", value=False)
        with col_b:
            submitted = st.form_submit_button("⚡ Triage Now", type="primary", use_container_width=True)

    if submitted and subject and body:
        with st.spinner("Running AI triage pipeline..."):
            t0 = time.time()
            try:
                resp = requests.post(
                    f"{API_BASE}/triage",
                    json={"ticket_id": ticket_id, "subject": subject, "body": body, "run_rag": run_rag},
                    timeout=120,
                )
                elapsed = (time.time() - t0) * 1000
                data = resp.json()

                # ── Result Cards ──
                st.divider()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Category", data["classification"]["category"].upper())
                c2.metric("Priority", data["classification"]["priority"].upper())
                c3.metric("Routing Team", data["routing_team"].upper())
                c4.metric("Auto-Escalate", "🔴 YES" if data["auto_escalate"] else "🟢 NO")

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Confidence", f"{data['classification']['confidence']:.0%}")
                c6.metric("SLA Risk", f"{data['sla_prediction']['sla_risk_score']:.0%}")
                c7.metric("SLA Level", data['sla_prediction']['risk_level'].upper())
                c8.metric("Total Latency", f"{elapsed:.0f}ms")

                if data.get("auto_escalate"):
                    st.warning(f"⚠️ **Escalation:** {data['escalation_reason']}")

                # ── Similar Tickets ──
                if data.get("similar_tickets"):
                    st.subheader("📎 Similar Historical Tickets")
                    sim_df = pd.DataFrame(data["similar_tickets"])
                    sim_df["similarity"] = sim_df["similarity"].apply(lambda x: f"{x:.0%}")
                    st.dataframe(sim_df[["ticket_id", "similarity", "category", "priority", "subject"]], use_container_width=True)

                # ── RAG Response ──
                if data.get("grounded_response"):
                    st.subheader("🤖 AI-Generated Grounded Response")
                    st.info(data["grounded_response"])

                # ── Timings ──
                with st.expander("⏱️ Pipeline Timing Breakdown"):
                    timings = data["timings_ms"]
                    timing_df = pd.DataFrame([
                        {"Step": k.replace("_ms", "").title(), "Latency (ms)": v}
                        for k, v in timings.items() if k != "total_ms"
                    ])
                    st.bar_chart(timing_df.set_index("Step"))

            except requests.exceptions.Timeout:
                st.error("Request timed out. The model may be loading. Try again in 5 seconds.")
            except Exception as e:
                st.error(f"Error: {e}")

    elif submitted:
        st.warning("Please fill in both Subject and Description.")


# ── Analytics Page ────────────────────────────────────────────────────────────
elif "📊" in page:
    st.title("📊 Triage Analytics")

    stats = get_stats()

    if stats["total"] == 0:
        st.info("No triage requests logged yet. Submit tickets on the Live Triage page.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Triaged", stats["total"])
        c2.metric("Auto-Escalated", stats["escalated"])
        c3.metric("Escalation Rate", f"{stats['escalation_rate']:.0%}")
        c4.metric("Avg Latency", f"{stats['avg_latency_ms']:.0f}ms")

        if stats["category_counts"]:
            st.subheader("Category Distribution")
            cat_df = pd.DataFrame(
                list(stats["category_counts"].items()),
                columns=["Category", "Count"]
            ).sort_values("Count", ascending=False)
            st.bar_chart(cat_df.set_index("Category"))


# ── Request Log Page ──────────────────────────────────────────────────────────
elif "🔍" in page:
    st.title("🔍 Request Log")
    st.caption("Last 50 triage requests logged from the API.")

    rows = get_recent(50)
    if not rows:
        st.info("No requests logged yet.")
    else:
        df = pd.DataFrame(rows)
        df["auto_escalate"] = df["auto_escalate"].map({1: "YES", 0: "no"})
        df["sla_risk"] = df["sla_risk"].apply(lambda x: f"{x:.0%}")
        df["confidence"] = df["confidence"].apply(lambda x: f"{x:.0%}")
        df["total_ms"] = df["total_ms"].apply(lambda x: f"{x:.0f}ms")
        st.dataframe(
            df[["ts", "ticket_id", "category", "priority", "routing_team",
                "auto_escalate", "sla_risk", "confidence", "total_ms"]],
            use_container_width=True
        )


# ── System Health Page ────────────────────────────────────────────────────────
elif "💚" in page:
    st.title("💚 System Health")

    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
        st.success("✅ API Server: Online")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Models")
            st.code(f"Primary LLM : {health['llm_model']}\nFallback LLM: {health['fallback_model']}\nEmbeddings  : {health['embed_model']}", language=None)
        with c2:
            st.subheader("Vector Index")
            st.metric("Indexed Tickets", f"{health['vector_index_size']:,}")
            st.caption("ChromaDB with BGE-M3 embeddings (cosine similarity)")

        st.subheader("Pipeline Architecture")
        st.code("""
New Ticket → POST /triage
    │
    ├── [1] LLM Cascade Classifier (gemma2:2b → gemma4:e4b fallback)
    ├── [2] LightGBM SLA Breach Predictor
    ├── [3] ChromaDB Semantic Search (68,235 vectors, ~4ms)
    ├── [4] Deterministic Routing Rules + SLA Override
    └── [5] RAG Response Generator (optional, gemma2:2b)
        """, language=None)

    except Exception:
        st.error("❌ API Server: Offline")
        st.code("uvicorn app.main:app --host 0.0.0.0 --port 8000", language="bash")
