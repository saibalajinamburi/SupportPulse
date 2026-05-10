# SupportPulse Intelligence Platform

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/saibalajiomg/SupportPulse)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue?logo=docker)](https://github.com/saibalajinamburi/SupportPulse/blob/main/docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](http://localhost:8000/docs)
[![Grafana](https://img.shields.io/badge/Grafana-Observability-orange?logo=grafana)](http://localhost:3000)

> **End-to-End Production MLOps | LLM Cascade · RAG · ChromaDB · LightGBM · FastAPI · Streamlit · Prometheus · Grafana**

A production-grade AI support ticket triage system that automatically classifies, prioritizes, routes, and generates grounded resolutions for support tickets — built with a full MLOps lifecycle from raw data ingestion through drift monitoring.

![Streamlit Live Triage Dashboard](Images/Streamlit_Live_Triage.png)

---

## Live Services

| Service | URL | Description |
|---|---|---|
| **HuggingFace Space** | [Live Demo](https://huggingface.co/spaces/saibalajiomg/SupportPulse) | Public interactive Gradio UI with pre-computed results |
| **FastAPI** | `http://localhost:8000/docs` | Swagger UI — interactive endpoint testing |
| **Streamlit Dashboard** | `http://localhost:8501` | 4-page monitoring & live AI triage UI |
| **MLflow UI** | `http://localhost:5000` | Experiment tracking & model registry |
| **DagsHub** | `https://dagshub.com/saibalajinamburi/SupportPulse` | Remote MLflow tracking & Data versioning (Optional) |
| **Grafana** | `http://localhost:3000` | DevOps observability & hardware metrics |
| **Prometheus** | `http://localhost:9090` | Time-series metrics scraper |

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         POST /triage (FastAPI)           │
                    └──────────────────┬──────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
┌─────────────────┐        ┌────────────────────┐       ┌────────────────────┐
│  LLM Cascade    │        │  LightGBM SLA      │       │  ChromaDB Vector   │
│  Classifier     │        │  Breach Predictor  │       │  Search (68k docs) │
│                 │        │                    │       │                    │
│  gemma2:2b  ──► │        │  18 structured     │       │  BGE-M3 embeddings │
│  (primary)      │        │  features → risk   │       │  cosine similarity │
│  gemma4:e4b ──► │        │  score 0.0-1.0     │       │  HNSW index ~2ms   │
│  (fallback)     │        │                    │       │                    │
└────────┬────────┘        └────────┬───────────┘       └────────┬───────────┘
         │                          │                             │
         └──────────────────────────┼─────────────────────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  Deterministic      │
                          │  Triage Agent       │
                          │                    │
                          │  Routing Rules +    │
                          │  SLA Override       │
                          └─────────┬──────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  RAG Generator      │
                          │  (optional)         │
                          │                    │
                          │  gemma2:2b +        │
                          │  grounding prompt   │
                          └─────────┬──────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  SQLite Observ.     │
                          │  Logger             │
                          │  + Drift Detector   │
                          │  + RAGAS Evaluator  │
                          └────────────────────┘
```

---

## Key Design Decisions

### 1. LLM Cascade — Why Two Models (`gemma2:2b` & `gemma4:e4b`)?
Using `gemma4:e4b` (a powerful, highly capable fallback model) for every ticket provides maximum accuracy but is slower and resource-intensive. Using `gemma2:2b` (a lightweight, ultra-fast primary model) is highly efficient but can sometimes struggle with complex, ambiguous edge cases.

The **Cascade Pattern** solves this: every ticket is routed through the fast `gemma2:2b` first. If its confidence score falls below 0.75, the system automatically escalates the ticket to the highly credible `gemma4:e4b` fallback model. Result: **~5 second average latency while retaining enterprise-grade large-model accuracy.**

### 2. Deterministic Routing Agent — Not LangChain
An autonomous LangChain agent might route a SQL injection ticket to the billing team if the ticket mentions payment data. With hardcoded routing rules, the decision is always auditable: `security + critical → security team, always`. For enterprise production, predictability beats autonomy.

### 3. RAG Over Fine-Tuning
Fine-tuning bakes knowledge into model weights — stale the moment new ticket patterns emerge. RAG retrieves from a live ChromaDB index. Adding new historical resolutions is as simple as inserting a new vector — zero retraining cost, instant knowledge refresh.

### 4. BGE-M3 for Embeddings
Supports 100+ languages and hybrid search (dense semantic + sparse keyword). Critical for support tickets where a user might describe a problem semantically but include specific error codes like `ECONNREFUSED` in the same sentence.

---

## Project Structure

```
SupportPulse/
├── app/                        # FastAPI gateway
│   ├── main.py                 # Lifespan pre-warming, 3 endpoints
│   ├── schemas.py              # Pydantic request/response models
│   └── config.py               # Settings management
├── dashboard/
│   └── streamlit_app.py        # 4-page Streamlit monitoring dashboard
├── src/
│   ├── agent/
│   │   └── triage_agent.py     # Deterministic orchestration agent
│   ├── features/
│   │   ├── embedding.py        # GPU-accelerated BGE-M3 batch embedding
│   │   └── structured_features.py  # 18-feature behavioral extraction
│   ├── models/
│   │   ├── classifier.py       # LLM Cascade classifier
│   │   └── sla_model.py        # LightGBM SLA breach predictor
│   ├── monitoring/
│   │   ├── request_logger.py   # SQLite observability logger
│   │   ├── rag_evaluator.py    # LLM-as-a-Judge RAGAS evaluation
│   │   └── drift_detector.py   # PSI + KL divergence drift detection
│   ├── rag/
│   │   ├── pipeline.py         # End-to-end RAG orchestration
│   │   └── prompt_builder.py   # Grounding prompt template
│   └── vector/
│       ├── indexer.py          # ChromaDB batch indexer
│       └── retriever.py        # Semantic similarity retrieval
├── scripts/
│   ├── test_api.py             # Full API test suite
│   └── evaluate_agent.py       # 20-ticket agent accuracy evaluation
├── feature_store/              # Feast feature store configuration
├── hf_space/                   # HuggingFace Spaces Gradio App
├── docker-compose.yml          # Container orchestration spec
└── requirements.txt            # All dependencies
```

---

## Dataset

- **Source**: GitHub Issues API + HuggingFace datasets + Synthetic generation
- **Raw (Bronze)**: 81,844 tickets
- **After cleaning (Silver)**: 68,235 tickets
  - PII masking: 24,970 detections removed
  - Deduplication: 13,609 duplicates removed
  - Label normalization: 12 canonical categories
- **Splits (Gold)**: 70% train / 15% val / 15% test (chronological)
- **Embeddings**: 68,235 × 1024 float32 vectors (BGE-M3, ~266MB)

---

## Model Performance

| Model | Metric | Value |
|---|---|---|
| LightGBM SLA Predictor | Test AUC | **0.74** |
| LightGBM SLA Predictor | Training time | 2.2 seconds |
| LLM Cascade Classifier | Accuracy (5 test cases) | **5/5 (100%)** |
| LLM Cascade Classifier | Avg latency (warm) | ~5 seconds |
| Triage Agent | Routing accuracy (20 tickets) | **80%** |
| Triage Agent | Escalation accuracy | **90%** |
| ChromaDB Retrieval | Recall@5 | **1.00 (100%)** |
| ChromaDB Retrieval | Avg query latency | **2.08ms** |
| RAG Generator (warm) | End-to-end latency | ~13 seconds |

---

## Running Locally

### Prerequisites
- Python 3.12+
- [Ollama](https://ollama.com/download) with models: `gemma2:2b`, `gemma4:e4b`, `bge-m3`
- 8GB+ RAM, GPU optional but recommended

### Setup
```bash
git clone https://github.com/saibalajinamburi/SupportPulse
cd SupportPulse
pip install -r requirements.txt
```

### Pull Ollama Models
```bash
ollama pull gemma2:2b
ollama pull bge-m3
# Optional (fallback model, 10GB):
ollama pull gemma4:e4b
```

### Start Services (Via Docker)
The easiest way to run the entire stack (FastAPI, Streamlit, MLflow, Prometheus, Grafana) is via Docker Compose:
```bash
docker-compose up -d
```

### Start Services (Manual Local)
```bash
# Terminal 1 — API Server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Dashboard
streamlit run dashboard/streamlit_app.py --server.port 8501

# Terminal 3 — MLflow UI (optional)
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

### Remote MLflow Tracking (DagsHub)
If you want to track experiments remotely instead of locally, set up DagsHub:
```bash
# 1. Set your credentials
export MLFLOW_TRACKING_URI="https://dagshub.com/saibalajinamburi/SupportPulse.mlflow"
export MLFLOW_TRACKING_USERNAME="saibalajinamburi"
export MLFLOW_TRACKING_PASSWORD="YOUR_DAGSHUB_TOKEN"

# 2. Run the pipeline - metrics will log to the cloud automatically
python src/pipeline/run_pipeline.py
```

### Test the API
```bash
python scripts/test_api.py
```

### Run Agent Evaluation
```bash
python scripts/evaluate_agent.py
```

### Run Drift Detection
```bash
python src/monitoring/drift_detector.py
```

---

## API Endpoints

### `GET /health`
Returns server status, model names, and vector index size.

### `POST /classify`
Fast classification endpoint — LLM Cascade only, no retrieval or RAG.
```json
{
  "subject": "Production database returning 500 errors",
  "body": "The API has been down for 20 minutes..."
}
```
Returns: `category`, `priority`, `routing_team`, `confidence`, `latency_ms`

### `POST /triage`
Full pipeline: classify → SLA predict → semantic retrieve → route → [RAG generate].
```json
{
  "ticket_id": "TICKET-001",
  "subject": "SQL injection vulnerability found",
  "body": "Attacker can bypass auth via ...",
  "run_rag": false
}
```
Returns: Full `TriageResponse` with classification, SLA risk, routing decision, similar tickets, and optional grounded response.

---

## MLOps Pipeline

```
Phase 1:  Raw Data Ingestion (GitHub API + HuggingFace + Synthetic)
Phase 2:  Data Engineering (PII masking, dedup, embeddings, Feast feature store)
Phase 3:  Model Training (LightGBM SLA + LLM Cascade classifier)
Phase 4:  Vector Index (ChromaDB, HNSW, 68k BGE-M3 vectors)
Phase 5:  RAG Pipeline (retrieve → ground → generate)
Phase 6:  Triage Agent (deterministic routing + SLA override)
Phase 7:  FastAPI Gateway (pre-warming, Pydantic validation, CORS)
Phase 8:  Observability (Streamlit dashboard + SQLite request logger)
Phase 9:  Evaluation (RAGAS LLM Judge + PSI drift detection)
```

---



## License

MIT License — see [LICENSE](./LICENSE)
