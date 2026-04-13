# analytics_service/analytics/train.py
# Author: Andrew Fox

# Loads training_data.csv, trains a multi-label Random Forest classifier,
# evaluates it with a train/test split, and saves the trained model to model.pkl.
# Run once by the developer before shipping the app.

# Usage: python -m analytics_service.analytics.train


import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier

from analytics_service.analytics.labels import LABEL_NAMES

DATA_PATH  = Path("analytics_service/data/training_data.csv")
MODEL_PATH = Path("analytics_service/data/model.pkl")


def train():
    print("Loading training data...")
    df = pd.read_csv(DATA_PATH)
    print(f"  {len(df)} rows, {len(df.columns)} columns")

    feature_cols = [c for c in df.columns if c not in LABEL_NAMES + ["source"]]
    X = df[feature_cols].values
    y = df[LABEL_NAMES].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"  Train: {len(X_train)}  Test: {len(X_test)}")

    print("\nTraining Random Forest...")
    base = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model = MultiOutputClassifier(base, n_jobs=-1)
    model.fit(X_train, y_train)

    print("\nEvaluating on test set...")
    y_pred = model.predict(X_test)

    for i, label in enumerate(LABEL_NAMES):
        report = classification_report(
            y_test[:, i], y_pred[:, i],
            target_names=["no", "yes"],
            zero_division=0,
            output_dict=True,
        )
        precision = report["yes"]["precision"]
        recall    = report["yes"]["recall"]
        f1        = report["yes"]["f1-score"]
        support   = int(report["yes"]["support"])
        print(f"  {label:<30}  P={precision:.2f}  R={recall:.2f}  F1={f1:.2f}  (support={support})")

    # Save feature column names alongside the model so model.py can align inputs
    payload = {
        "model":        model,
        "feature_cols": feature_cols,
        "label_names":  LABEL_NAMES,
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)

    print(f"\nModel saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
