# analytics_service/visualisations/plot_confusion_matrices.py
# Author: Andrew Fox

# Generates confusion matrices for all 12 labels on the held-out test set.
# Each matrix shows true positives, false positives, true negatives, false negatives.
# Usage: python -m analytics_service.visualisations.plot_confusion_matrices

import pickle
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

from analytics_service.analytics.labels import LABEL_NAMES

DATA_PATH  = Path("analytics_service/data/training_data.csv")
MODEL_PATH = Path("analytics_service/data/model.pkl")
OUT_PATH   = Path("analytics_service/visualisations/model_confusion_matrices.png")


def main():
    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model        = payload["model"]
    feature_cols = payload["feature_cols"]

    df = pd.read_csv(DATA_PATH)
    X = df[feature_cols].values
    y = df[LABEL_NAMES].values

    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    y_pred = model.predict(X_test)

    fig, axes = plt.subplots(3, 4, figsize=(18, 12))
    axes = axes.flatten()

    for i, label in enumerate(LABEL_NAMES):
        cm = confusion_matrix(y_test[:, i], y_pred[:, i])
        ax = axes[i]

        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        ax.set_title(label.replace("_", " "), fontsize=9, pad=6)
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Predicted No", "Predicted Yes"], fontsize=7)
        ax.set_yticklabels(["Actual No", "Actual Yes"], fontsize=7)

        for row in range(cm.shape[0]):
            for col in range(cm.shape[1]):
                val = cm[row, col]
                color = "white" if val > cm.max() / 2 else "black"
                ax.text(col, row, str(val), ha="center", va="center",
                        fontsize=11, color=color, fontweight="bold")

    fig.suptitle("Confusion Matrices — All 12 Labels (test set)", fontsize=14, y=1.01)
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
