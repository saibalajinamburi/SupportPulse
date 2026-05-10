"""Evaluate Zero-Shot Classifier against Gold Test Set."""

import pandas as pd
import time
from pathlib import Path
import mlflow
from sklearn.metrics import classification_report, accuracy_score
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.models.classifier import classify_batch
from app.config import settings

GOLD_TEST_PATH = Path("data/gold/test.parquet")


def evaluate(sample_size: int = 500):
    """Evaluate the LLM Cascade classifier against the holdout test set."""
    primary = settings.OLLAMA_LLM_MODEL
    fallback = settings.OLLAMA_FALLBACK_MODEL

    print("=" * 60)
    print("  SupportPulse - Cascade Classifier Evaluation")
    print(f"  Primary  : {primary}")
    print(f"  Fallback : {fallback}")
    print(f"  Sample   : {sample_size} tickets")
    print("=" * 60)

    df = pd.read_parquet(GOLD_TEST_PATH)
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42)

    tickets = df[["ticket_id", "subject", "body"]].to_dict("records")
    y_true = df["category"].str.lower().str.strip().tolist()

    print(f"\n  [Eval] Running cascade inference on {len(tickets)} tickets...")
    start_time = time.time()
    predictions = classify_batch(tickets, show_progress=True)
    elapsed = time.time() - start_time

    y_pred = [p.get("category", "question").lower().strip() for p in predictions]
    escalated = sum(1 for p in predictions if p.get("escalated"))
    
    # 3. Calculate Metrics
    accuracy = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, zero_division=0, output_dict=True)
    
    # Extract macro metrics
    macro_precision = report["macro avg"]["precision"]
    macro_recall = report["macro avg"]["recall"]
    macro_f1 = report["macro avg"]["f1-score"]

    print("\n" + "=" * 60)
    print(f"  EVALUATION RESULTS ({len(tickets)} tickets)")
    print("=" * 60)
    print(f"  Total Time : {elapsed:.1f}s (Avg: {(elapsed/len(tickets)):.2f}s/ticket)")
    print(f"  Accuracy   : {accuracy:.4f}")
    print(f"  Precision  : {macro_precision:.4f} (Macro)")
    print(f"  Recall     : {macro_recall:.4f} (Macro)")
    print(f"  F1-Score   : {macro_f1:.4f} (Macro)")
    print("=" * 60)
    
    # Print per-class metrics for top classes
    print("\n  Per-Class F1 Scores:")
    for label, metrics in report.items():
        if isinstance(metrics, dict) and label not in ("accuracy", "macro avg", "weighted avg"):
            if metrics["support"] > 0:
                print(f"    {label:<15}: {metrics['f1-score']:.4f} (n={metrics['support']})")

    # Log to MLflow
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment("classifier_evaluation")

    run_name = f"cascade_{primary.replace(':', '_')}_fb_{fallback.replace(':', '_')}"
    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("primary_model", primary)
        mlflow.log_param("fallback_model", fallback)
        mlflow.log_param("sample_size", len(tickets))
        mlflow.log_metrics({
            "accuracy": accuracy,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
            "avg_latency_sec": elapsed / len(tickets),
            "escalation_rate": escalated / len(tickets),
        })
        print(f"\n  Escalation Rate : {escalated}/{len(tickets)} ({escalated/len(tickets)*100:.1f}% used fallback)")
        print(f"  Logged to MLflow: {mlflow.active_run().info.run_id}")

if __name__ == "__main__":
    evaluate()
