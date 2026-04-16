# analytics_service/visualisations/plot_label_f1.py
# Author: Andrew Fox

# Heatmap of Precision, Recall, and F1 per label on the held-out test set.
# Usage: python -m analytics_service.visualisations.plot_label_f1

import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from analytics_service.analytics.labels import LABEL_NAMES

DATA_PATH  = Path("analytics_service/data/training_data.csv")
MODEL_PATH = Path("analytics_service/data/model.pkl")
OUT_PATH   = Path("analytics_service/visualisations/model_label_f1_scores.png")


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

    metrics = []
    for i in range(len(LABEL_NAMES)):
        r = classification_report(y_test[:, i], y_pred[:, i], output_dict=True, zero_division=0)
        pos = r.get("1", {})
        metrics.append([
            pos.get("precision", 0.0),
            pos.get("recall",    0.0),
            pos.get("f1-score",  0.0),
        ])

    data = np.array(metrics)   # shape (12, 3)

    # Clamp colour range so small differences near 1.0 are visible
    vmin = max(0.0, data.min() - 0.05)

    fig, ax = plt.subplots(figsize=(6, 8))
    im = ax.imshow(data, aspect="auto", cmap="Blues", vmin=vmin, vmax=1.0)

    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["Precision", "Recall", "F1"], fontsize=11)
    ax.set_yticks(range(len(LABEL_NAMES)))
    ax.set_yticklabels([l.replace("_", " ") for l in LABEL_NAMES], fontsize=10)
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()

    for i in range(len(LABEL_NAMES)):
        for j in range(3):
            val = data[i, j]
            colour = "white" if val > (vmin + 1.0) / 2 else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=9, color=colour)

    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    ax.set_title("Precision / Recall / F1 per label (test set)", pad=14, fontsize=12)
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
