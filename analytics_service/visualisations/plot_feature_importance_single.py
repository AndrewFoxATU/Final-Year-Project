# analytics_service/visualisations/plot_feature_importance_single.py
# Author: Andrew Fox

# Feature importance for one specific label's Random Forest.
# Shows which features the model relies on most to detect that issue.
# Usage: python -m analytics_service.visualisations.plot_feature_importance_single

import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from analytics_service.analytics.labels import LABEL_NAMES

MODEL_PATH = Path("analytics_service/data/model.pkl")
OUT_DIR    = Path("analytics_service/visualisations")

# Labels worth showing individually — ones with interesting feature patterns
LABELS_TO_PLOT = [
    "cpu_thermal_throttle",
    "ram_memory_leak",
    "gpu_power_throttle",
]


def plot_single(model, feature_cols, label, out_dir):
    label_idx    = LABEL_NAMES.index(label)
    forest       = model.estimators_[label_idx]
    importances  = forest.feature_importances_
    indices      = np.argsort(importances)[-15:]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(
        [feature_cols[i] for i in indices],
        importances[indices],
        color="steelblue"
    )
    ax.set_xlabel("Feature importance")
    ax.set_title(f"Top 15 features — {label.replace('_', ' ')}")
    plt.tight_layout()

    out_path = out_dir / f"importance_{label}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def main():
    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model        = payload["model"]
    feature_cols = payload["feature_cols"]

    for label in LABELS_TO_PLOT:
        plot_single(model, feature_cols, label, OUT_DIR)


if __name__ == "__main__":
    main()
