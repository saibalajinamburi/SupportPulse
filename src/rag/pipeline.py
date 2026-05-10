"""RAG Pipeline — retrieval-augmented response generation for support tickets."""

import time
import ollama
from app.config import settings
from src.vector.retriever import retrieve_similar
from src.models.classifier import classify_ticket
from src.rag.prompt_builder import build_rag_prompt


def run_rag_pipeline(
    subject: str,
    body: str,
    top_k: int = 3,
    generator_model: str = None,
) -> dict:
    """
    Full RAG pipeline for a single ticket:
    1. Classify (LLM Cascade: gemma2:2b → gemma4:e4b if uncertain)
    2. Retrieve top-K similar historical tickets from ChromaDB
    3. Build grounded prompt with retrieved context
    4. Generate response using fast generator model (gemma2:2b)

    Returns a structured dict with classification, retrieved context, and grounded response.
    """
    generator = generator_model or settings.OLLAMA_LLM_MODEL
    timings = {}
    result = {"subject": subject, "body": body[:200]}

    # Step 1: Classify
    t0 = time.time()
    classification = classify_ticket(
        subject=subject,
        body=body,
        model=settings.OLLAMA_LLM_MODEL,
        fallback_model=settings.OLLAMA_FALLBACK_MODEL,
    )
    timings["classify_ms"] = round((time.time() - t0) * 1000, 1)
    result["classification"] = classification

    category = classification.get("category", "question")
    priority = classification.get("priority", "medium")

    # Step 2: Retrieve similar tickets
    t0 = time.time()
    query_text = f"{subject} {body}"
    retrieved = retrieve_similar(query_text, top_k=top_k)
    timings["retrieve_ms"] = round((time.time() - t0) * 1000, 1)
    result["retrieved_tickets"] = retrieved

    # Step 3: Build grounded prompt
    system_prompt, user_prompt = build_rag_prompt(
        subject=subject,
        body=body,
        category=category,
        priority=priority,
        retrieved_tickets=retrieved,
    )

    # Step 4: Generate grounded response
    t0 = time.time()
    try:
        response = ollama.chat(
            model=generator,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "temperature": 0.2,
                "num_predict": 512,
                "num_gpu": 99,
            }
        )
        result["response"] = response["message"]["content"]
    except Exception as e:
        result["response"] = f"[Generation failed: {e}]"
    timings["generate_ms"] = round((time.time() - t0) * 1000, 1)

    timings["total_ms"] = sum(timings.values())
    result["timings"] = timings
    result["generator_model"] = generator
    return result
