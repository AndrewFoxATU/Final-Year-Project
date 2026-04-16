# analytics_service/visualisations/plot_data_split.py
# Author: Andrew Fox

# Pie chart showing the synthetic vs real split in the training dataset.
# Usage: python -m analytics_service.visualisations.plot_data_split

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_PATH = Path("analytics_service/data/training_data.csv")
OUT_PATH  = Path("analytics_service/visualisations/data_synthetic_vs_real.png")


def main():
    df = pd.read_csv(DATA_PATH)
    counts = df["source"].value_counts()

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%",
           colors=["steelblue", "coral"])
    ax.set_title("Training data: Synthetic vs Real")
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150)
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
