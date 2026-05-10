"""LightGBM SLA Breach Model — trainer with progress tracking and local MLflow."""

import time
import dagshub
import datetime
import numpy as np
import pandas as pd
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import joblib
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

FEATURE_COLS = [
    "text_length", "word_count", "subject_length",
    "code_block_count", "url_count", "question_mark_count",
    "exclamation_count", "caps_word_count",
    "hour_of_day", "day_of_week", "is_weekend", "is_after_hours",
    "ticket_age_hours", "reopen_count", "comment_count",
    "customer_tier_encoded", "source_encoded"
]

SLA_BREACH_CATEGORIES = {"incident", "sla_breach", "security"}
GOLD_DIR = Path("data/gold")
MODEL_DIR = Path("models")

# ── Progress tracking state ──────────────────────────────────────────────────
_start_time = None
_current_iter = 0
_total_iters = 500


class ProgressCallback:
    """Real-time training progress with ETA."""

    def __init__(self, total: int):
        self.total = total
        self.start = time.time()

    def __call__(self, env):
        global _current_iter
        iteration = env.iteration + 1
        _current_iter = iteration

        if iteration % 50 == 0 or iteration == self.total:
            elapsed = time.time() - self.start
            rate = iteration / elapsed if elapsed > 0 else 1
            remaining = (self.total - iteration) / rate if rate > 0 else 0
            pct = (iteration / self.total) * 100

            val_loss = None
            for name, metric, score, _ in env.evaluation_result_list:
                if "binary_logloss" in metric:
                    val_loss = score

            eta_str = str(datetime.timedelta(seconds=int(remaining)))
            loss_str = f"  val_loss={val_loss:.4f}" if val_loss is not None else ""
            print(
                f"  [SLA] {pct:5.1f}% | iter {iteration}/{self.total}"
                f"{loss_str}  |  elapsed={elapsed:.0f}s  ETA={eta_str}"
            )


def _build_sla_label(df: pd.DataFrame) -> pd.Series:
    """Binary SLA breach label: 1 if category is high-risk."""
    return df["category"].isin(SLA_BREACH_CATEGORIES).astype(int)


def load_split(split: str) -> pd.DataFrame:
    """Load and merge features with category labels for a given split."""
    raw = pd.read_parquet(GOLD_DIR / f"{split}.parquet")
    features = pd.read_parquet(GOLD_DIR / f"{split}_features.parquet")
    return features.merge(raw[["ticket_id", "category"]], on="ticket_id", how="left")


def train() -> Path:
    """Train the LightGBM SLA breach model with progress tracking and MLflow."""
    global _start_time, _total_iters
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    _start_time = time.time()


    dagshub.init(repo_owner='saibalajinamburi', repo_name='SupportPulse', mlflow=True)
    mlflow.set_experiment("sla_breach_prediction")

    print("=" * 60)
    print("  SupportPulse — SLA Breach Model Training")
    print("=" * 60)
    print("  Model: LightGBM 4.6 (CPU — tabular data, ~60s expected)")
    print("  Note: GPU Ollama inference runs separately in classifier.py")
    print("=" * 60)

    print("\n  [SLA] Loading datasets...")
    train_df = load_split("train")
    val_df = load_split("val")
    test_df = load_split("test")

    X_train = train_df[FEATURE_COLS].fillna(0)
    y_train = _build_sla_label(train_df)
    X_val = val_df[FEATURE_COLS].fillna(0)
    y_val = _build_sla_label(val_df)
    X_test = test_df[FEATURE_COLS].fillna(0)
    y_test = _build_sla_label(test_df)

    pos_rate = y_train.mean()
    scale_pos = max(1.0, (1 - pos_rate) / pos_rate) if pos_rate > 0 else 1.0

    print(f"  [SLA] Train:  {len(X_train):,} rows | Positive (breach): {y_train.sum():,} ({pos_rate:.1%})")
    print(f"  [SLA] Val:    {len(X_val):,} rows")
    print(f"  [SLA] Test:   {len(X_test):,} rows")
    print(f"  [SLA] Class imbalance weight: {scale_pos:.2f}x")

    n_estimators = 500
    _total_iters = n_estimators

    params = {
        "objective": "binary",
        "metric": ["binary_logloss", "auc"],
        "num_leaves": 63,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "min_child_samples": 20,
        "n_estimators": n_estimators,
        "scale_pos_weight": scale_pos,
        "random_state": 42,
        "verbose": -1,
        "n_jobs": -1,
    }

    print(f"\n  [SLA] Starting training — 0.0% | iter 0/{n_estimators} | ETA calculating...")

    with mlflow.start_run(run_name="lgbm_sla_v1"):
        mlflow.log_params(params)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("positive_rate", float(pos_rate))

        model = lgb.LGBMClassifier(**params)

        progress_cb = ProgressCallback(n_estimators)

        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[
                lgb.early_stopping(50, verbose=False),
                lgb.log_evaluation(-1),
                progress_cb,
            ]
        )

        # ── Validation metrics ───────────────────────────────────────────────
        val_preds = model.predict(X_val)
        val_proba = model.predict_proba(X_val)[:, 1]
        val_auc = roc_auc_score(y_val, val_proba)
        val_f1 = f1_score(y_val, val_preds, zero_division=0)
        val_precision = precision_score(y_val, val_preds, zero_division=0)
        val_recall = recall_score(y_val, val_preds, zero_division=0)

        # ── Test metrics ─────────────────────────────────────────────────────
        test_preds = model.predict(X_test)
        test_proba = model.predict_proba(X_test)[:, 1]
        test_auc = roc_auc_score(y_test, test_proba)
        test_f1 = f1_score(y_test, test_preds, zero_division=0)
        test_precision = precision_score(y_test, test_preds, zero_division=0)
        test_recall = recall_score(y_test, test_preds, zero_division=0)

        mlflow.log_metrics({
            "val_auc": val_auc, "val_f1": val_f1,
            "val_precision": val_precision, "val_recall": val_recall,
            "test_auc": test_auc, "test_f1": test_f1,
            "test_precision": test_precision, "test_recall": test_recall,
        })

        # ── Feature importance ───────────────────────────────────────────────
        fi = pd.Series(
            model.feature_importances_, index=FEATURE_COLS
        ).sort_values(ascending=False)

        total_elapsed = time.time() - _start_time

        print(f"\n{'=' * 60}")
        print(f"  TRAINING COMPLETE — {total_elapsed:.1f}s")
        print(f"{'=' * 60}")
        print(f"  Val  AUC:       {val_auc:.4f}")
        print(f"  Val  F1:        {val_f1:.4f}")
        print(f"  Val  Precision: {val_precision:.4f}")
        print(f"  Val  Recall:    {val_recall:.4f}")
        print(f"  Test AUC:       {test_auc:.4f}")
        print(f"  Test F1:        {test_f1:.4f}")
        print("\n  Top Features by Importance:")
        for feat, imp in fi.head(8).items():
            bar_len = int(imp / fi.max() * 20)
            bar = "#" * bar_len + "-" * (20 - bar_len)
            print(f"    {feat:<25} [{bar}] {imp:.0f}")

        # ── Save model ───────────────────────────────────────────────────────
        model_path = MODEL_DIR / "sla_model.joblib"
        joblib.dump(model, model_path)
        mlflow.log_artifact(str(model_path))

        run_id = mlflow.active_run().info.run_id
        print(f"\n  Model saved: {model_path}")
        print(f"  MLflow run:  {run_id}")
        print(f"{'=' * 60}\n")

    return model_path


if __name__ == "__main__":
    train()
