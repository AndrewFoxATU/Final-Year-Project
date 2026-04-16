# analytics_service/visualisations/plot_class_imbalance.py
# Author: Andrew Fox

# Bar chart showing the positive vs negative class ratio per label.
# Highlights how imbalanced each label is in the training data.
# Usage: python -m analytics_service.visualisations.plot_class_imbalance

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

from analytics_service.analytics.labels import LABEL_NAMES

DATA_PATH = Path("analytics_service/data/training_data.csv")
OUT_PATH  = Path("analytics_service/visualisations/data_class_imbalance.png")


def main():
    df = pd.read_csv(DATA_PATH)
    total = len(df)

    positives = df[LABEL_NAMES].sum().values.astype(int)
    negatives = total - positives

    y = np.arange(len(LABEL_NAMES))
    tick_labels = [l.replace("_", " ") for l in LABEL_NAMES]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(y, negatives, color="steelblue", label="Negative")
    ax.barh(y, positives, left=negatives, color="coral", label="Positive")

    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=10)
    ax.set_xlabel("Row count")
    ax.set_title("Class imbalance per label (positive vs negative)")
    ax.axvline(total, color="grey", linestyle="--", linewidth=0.8, alpha=0.5)

    for i, (pos, neg) in enumerate(zip(positives, negatives)):
        pct = pos / total * 100
        ax.text(total + total * 0.005, i, f"{pct:.1f}% pos",
                va="center", fontsize=8, color="dimgrey")

    neg_patch = mpatches.Patch(color="steelblue", label="Negative")
    pos_patch = mpatches.Patch(color="coral",     label="Positive")
    ax.legend(handles=[neg_patch, pos_patch])

    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
