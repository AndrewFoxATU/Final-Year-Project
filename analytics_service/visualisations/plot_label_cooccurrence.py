# analytics_service/visualisations/plot_label_cooccurrence.py
# Author: Andrew Fox

# Heatmap showing how often each pair of labels co-occurs in the training data.
# Each cell (i, j) shows what percentage of label i's positive rows also have label j.
# Usage: python -m analytics_service.visualisations.plot_label_cooccurrence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from analytics_service.analytics.labels import LABEL_NAMES

DATA_PATH = Path("analytics_service/data/training_data.csv")
OUT_PATH  = Path("analytics_service/visualisations/data_label_cooccurrence.png")


def main():
    df = pd.read_csv(DATA_PATH)
    labels = df[LABEL_NAMES].values.astype(int)
    n = len(LABEL_NAMES)

    # co[i, j] = % of rows where label i=1 that also have label j=1
    matrix = np.zeros((n, n))
    for i in range(n):
        pos_i = labels[:, i] == 1
        count_i = pos_i.sum()
        if count_i == 0:
            continue
        for j in range(n):
            matrix[i, j] = (pos_i & (labels[:, j] == 1)).sum() / count_i * 100

    tick_labels = [l.replace("_", " ") for l in LABEL_NAMES]

    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=100)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(tick_labels, fontsize=9)

    for i in range(n):
        for j in range(n):
            val = matrix[i, j]
            colour = "white" if val > 55 else "black"
            text = f"{val:.0f}%" if val > 0 else ""
            ax.text(j, i, text, ha="center", va="center", fontsize=8, color=colour)

    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label="% co-occurrence")
    ax.set_title("Label co-occurrence — % of row label's positives that also fire column label",
                 fontsize=11, pad=12)
    ax.set_ylabel("Row label (given positive)")
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
