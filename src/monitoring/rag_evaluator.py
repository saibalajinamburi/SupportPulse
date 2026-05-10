"""
Automated RAG Evaluation using the LLM-as-a-Judge pattern.
Grades the RAG pipeline's outputs for Faithfulness, Relevance, and Context Precision.
"""

import json
import ollama
from typing import Dict
from app.config import settings

EVAL_MODEL = settings.OLLAMA_FALLBACK_MODEL  # Use the larger model (gemma4) as the judge

def evaluate_faithfulness(question: str, context: str, answer: str) -> Dict:
    """
    Checks if the answer contains hallucinations.
    Returns a score 0.0 to 1.0 and reasoning.
    """
    prompt = f"""
    You are an expert grading system. Your task is to evaluate the FAITHFULNESS of an answer given a context.
    An answer is faithful if all the claims made in the answer can be inferred directly from the context.
    
    Question: {question}
    Context: {context}
    Answer: {answer}
    
    Output JSON strictly in this format:
    {{"score": 1.0, "reason": "short explanation of why"}}
    
    If the answer makes up information NOT in the context, score should be lower.
    """
    
    try:
        res = ollama.chat(
            model=EVAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.0}
        )
        result = json.loads(res["message"]["content"])
        return {"score": float(result.get("score", 0.0)), "reason": result.get("reason", "")}
    except Exception as e:
        return {"score": 0.0, "reason": f"Eval failed: {e}"}

def evaluate_answer_relevance(question: str, answer: str) -> Dict:
    """
    Checks if the answer directly addresses the user's question.
    """
    prompt = f"""
    You are an expert grading system. Evaluate the RELEVANCE of the answer to the question.
    Does it directly address the issue? Is it complete?
    
    Question: {question}
    Answer: {answer}
    
    Output JSON strictly in this format:
    {{"score": 1.0, "reason": "short explanation"}}
    
    Score 1.0 = Perfectly relevant. Score 0.0 = Completely irrelevant.
    """
    
    try:
        res = ollama.chat(
            model=EVAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.0}
        )
        result = json.loads(res["message"]["content"])
        return {"score": float(result.get("score", 0.0)), "reason": result.get("reason", "")}
    except Exception as e:
        return {"score": 0.0, "reason": f"Eval failed: {e}"}

def run_full_evaluation(ticket_id: str, subject: str, body: str, context_tickets: list, generated_response: str) -> Dict:
    """Run all RAGAS-style evaluations on a single interaction."""
    
    question = f"{subject}\n{body}"
    
    # Format context like we do in prompt_builder
    context_text = "\n\n".join([
        f"Historical Ticket {t['ticket_id']} [{t['category']}]:\n{t['subject']}"
        for t in context_tickets
    ])
    
    faithfulness = evaluate_faithfulness(question, context_text, generated_response)
    relevance = evaluate_answer_relevance(question, generated_response)
    
    return {
        "ticket_id": ticket_id,
        "metrics": {
            "faithfulness": faithfulness["score"],
            "relevance": relevance["score"]
        },
        "reasoning": {
            "faithfulness": faithfulness["reason"],
            "relevance": relevance["reason"]
        }
    }

if __name__ == "__main__":
    # Test the evaluator with a dummy example
    print(f"Loading Evaluator Judge: {EVAL_MODEL}...")
    
    q = "API is returning 500 errors"
    ctx = "Historical Ticket 1: 500 errors caused by database connection pool exhaustion. Fix: restart pgbouncer."
    ans = "The issue is likely database connection pool exhaustion. You should restart pgbouncer."
    
    print("Testing Faithfulness...")
    f_res = evaluate_faithfulness(q, ctx, ans)
    print(f"Score: {f_res['score']} | Reason: {f_res['reason']}")
    
    print("Testing Relevance...")
    r_res = evaluate_answer_relevance(q, ans)
    print(f"Score: {r_res['score']} | Reason: {r_res['reason']}")
