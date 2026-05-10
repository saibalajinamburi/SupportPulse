"""
Model Drift Detection Script.
Calculates Concept Drift (changes in label distribution) by comparing
the category distribution in the training data vs. the live triage logs.
Uses Kullback-Leibler (KL) Divergence and Population Stability Index (PSI).
"""

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from scipy.stats import entropy

DB_PATH = Path("data/requests.db")
TRAIN_PARQUET = Path("data/gold/train.parquet")

def get_train_distribution() -> pd.Series:
    """Get category distribution from training data."""
    if not TRAIN_PARQUET.exists():
        raise FileNotFoundError(f"Missing {TRAIN_PARQUET}")
    df = pd.read_parquet(TRAIN_PARQUET)
    dist = df["category"].value_counts(normalize=True)
    return dist

def get_live_distribution() -> pd.Series:
    """Get category distribution from live API request logs."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Missing {DB_PATH}")
    
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT category FROM triage_log", conn)
        
    if len(df) == 0:
        return pd.Series(dtype=float)
        
    dist = df["category"].value_counts(normalize=True)
    return dist

def calculate_psi(expected: pd.Series, actual: pd.Series) -> float:
    """Calculate Population Stability Index (PSI)."""
    # Align indices
    categories = expected.index.union(actual.index)
    
    # Add a tiny epsilon to avoid divide by zero or log(0)
    eps = 1e-4
    
    exp = expected.reindex(categories).fillna(0) + eps
    act = actual.reindex(categories).fillna(0) + eps
    
    # Normalize again after adding epsilon
    exp = exp / exp.sum()
    act = act / act.sum()
    
    psi = np.sum((act - exp) * np.log(act / exp))
    return float(psi)

def calculate_kl_divergence(expected: pd.Series, actual: pd.Series) -> float:
    """Calculate KL Divergence."""
    categories = expected.index.union(actual.index)
    eps = 1e-4
    
    exp = expected.reindex(categories).fillna(0) + eps
    act = actual.reindex(categories).fillna(0) + eps
    
    exp = exp / exp.sum()
    act = act / act.sum()
    
    return float(entropy(act, exp))

def run_drift_check():
    """Run full drift evaluation."""
    print("Running Drift Detection...\n")
    
    try:
        train_dist = get_train_distribution()
        live_dist = get_live_distribution()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
        
    if live_dist.empty:
        print("Not enough live data to calculate drift. Submit tickets to API first.")
        return
        
    print(f"Comparing {len(train_dist)} training categories vs {len(live_dist)} live categories.")
    
    psi = calculate_psi(train_dist, live_dist)
    kl_div = calculate_kl_divergence(train_dist, live_dist)
    
    print("\n--- Drift Metrics ---")
    print(f"Population Stability Index (PSI): {psi:.4f}")
    print(f"KL Divergence:                    {kl_div:.4f}")
    
    print("\n--- Interpretation ---")
    if psi < 0.1:
        print("✅ No significant drift detected (PSI < 0.1).")
    elif psi < 0.2:
        print("⚠️ Slight drift detected (0.1 <= PSI < 0.2). Monitor closely.")
    else:
        print("🚨 SIGNIFICANT DRIFT DETECTED (PSI >= 0.2). Model retraining recommended!")
        
if __name__ == "__main__":
    run_drift_check()
