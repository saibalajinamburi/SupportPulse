---
title: SupportPulse Intelligence Platform
emoji: 🎯
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.14.0
app_file: app.py
pinned: true
license: mit
short_description: End-to-End MLOps AI support ticket triage system
---

# SupportPulse Intelligence Platform

**End-to-End MLOps | LLM Cascade · RAG · ChromaDB · LightGBM · FastAPI**

## What This Demo Shows

This interactive demo showcases the SupportPulse AI triage pipeline. Enter any support ticket and the system will:

1. **Classify** the ticket (incident/bug/security/billing/...) using an LLM Cascade (gemma2:2b -> gemma4:e4b)
2. **Predict SLA breach risk** using a LightGBM model trained on 47,000 labeled tickets
3. **Retrieve** the 3 most similar historical tickets from a ChromaDB vector store (68,235 tickets, BGE-M3 embeddings)
4. **Route** to the correct team using deterministic rules + SLA override
5. **Generate** a grounded resolution using RAG (retrieval-augmented generation)

## Demo Note

This Space runs pre-computed examples since Ollama/GPU inference is not available on HuggingFace Spaces free tier.
The full pipeline with live models runs locally in ~5 seconds per ticket.

## Full Project

- **GitHub:** [saibalajinamburi/SupportPulse](https://github.com/saibalajinamburi/SupportPulse)
- **Tech Stack:** FastAPI, Streamlit, ChromaDB, LightGBM, Ollama (gemma2:2b, BGE-M3), SQLite, GitHub Actions CI/CD
- **Dataset:** 68,235 support tickets (GitHub Issues + HuggingFace + synthetic)

## Architecture

```
POST /triage
  |
  +-- [1] LLM Cascade Classifier (gemma2:2b -> gemma4:e4b fallback)
  +-- [2] LightGBM SLA Breach Predictor (AUC 0.74)
  +-- [3] ChromaDB Semantic Search (68k vectors, ~2ms)
  +-- [4] Deterministic Routing Rules + SLA Override
  +-- [5] RAG Response Generator (gemma2:2b + grounding prompt)
       |
       +-- SQLite Observability Logger
```
