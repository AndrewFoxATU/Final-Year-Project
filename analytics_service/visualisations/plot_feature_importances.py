# analytics_service/visualisations/plot_feature_importances.py
# Author: Andrew Fox

# Horizontal bar chart of the top 20 most important features averaged across
# all per-label trees in the Random Forest.
# Usage: python -m analytics_service.visualisations.plot_feature_importances

import pickle
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

MODEL_PATH = Path("analytics_service/data/model.pkl")
OUT_PATH   = Path("analytics_service/visualisations/model_feature_importances.png")


def main():
    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model        = payload["model"]
    feature_cols = payload["feature_cols"]
    label_names  = payload["label_names"]

    # Average feature importances across all per-label forests
    all_importances = np.array([
        est.feature_importances_
        for label_est in model.estimators_
        for est in label_est.estimators_
    ])
    mean_importances = all_importances.mean(axis=0)

    top_n = 20
    indices = np.argsort(mean_importances)[-top_n:]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(
        [feature_cols[i] for i in indices],
        mean_importances[indices],
        color="steelblue"
    )
    ax.set_xlabel("Mean importance")
    ax.set_title(f"Top {top_n} feature importances (averaged across all trees)")
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150)
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
