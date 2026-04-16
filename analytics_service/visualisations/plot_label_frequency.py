# analytics_service/visualisations/plot_label_frequency.py
# Author: Andrew Fox

# Stacked bar chart showing synthetic vs real label counts in the training dataset.
# Both counts are derived directly from training_data.csv.
# Usage: python -m analytics_service.visualisations.plot_label_frequency

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from analytics_service.analytics.labels import LABEL_NAMES

DATA_PATH = Path("analytics_service/data/training_data.csv")
OUT_PATH  = Path("analytics_service/visualisations/data_label_frequency.png")


def main():
    df = pd.read_csv(DATA_PATH)
    synthetic_counts = df[df["source"] == "synthetic"][LABEL_NAMES].sum().values
    real_counts      = df[df["source"] == "real"][LABEL_NAMES].sum().values

    y = np.arange(len(LABEL_NAMES))

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(y, synthetic_counts, label="Synthetic", color="coral")
    ax.barh(y, real_counts, left=synthetic_counts, label="Real", color="steelblue")

    ax.set_yticks(y)
    ax.set_yticklabels(LABEL_NAMES)
    ax.set_xlabel("Count")
    ax.set_title("Label frequency in training data — Synthetic vs Real")
    ax.legend()

    for i, (s, r) in enumerate(zip(synthetic_counts, real_counts)):
        total = s + r
        ax.text(total + 10, i, str(total), va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150)
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
