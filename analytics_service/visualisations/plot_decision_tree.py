# analytics_service/visualisations/plot_decision_tree.py
# Author: Andrew Fox

# Generates full decision tree visualisations for selected labels.
# Picks the shallowest tree from each label's forest so the full tree is readable.
# Usage: python -m analytics_service.visualisations.plot_decision_tree

import pickle
import matplotlib.pyplot as plt
from sklearn.tree import plot_tree
from pathlib import Path

from analytics_service.analytics.labels import LABEL_NAMES

MODEL_PATH = Path("analytics_service/data/model.pkl")
OUT_DIR    = Path("analytics_service/visualisations")

def plot_label_tree(model, feature_cols, label, out_dir):
    label_idx = LABEL_NAMES.index(label)
    forest    = model.estimators_[label_idx]
    tree      = min(forest.estimators_, key=lambda t: t.get_n_leaves())

    depth   = tree.get_depth()
    n_leaves = tree.get_n_leaves()

    fig_w = max(18, n_leaves * 4)
    fig_h = max(6,  depth * 3)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    plot_tree(
        tree,
        feature_names=feature_cols,
        class_names=["no", "yes"],
        filled=True,
        ax=ax,
        fontsize=10,
        impurity=False,
        proportion=False,
    )
    ax.set_title(f"Decision tree — {label}  (depth={depth}, leaves={n_leaves})", fontsize=13)
    plt.tight_layout()

    out_path = out_dir / f"tree_{label}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path}")


def main():
    with open(MODEL_PATH, "rb") as f:
        payload = pickle.load(f)
    model        = payload["model"]
    feature_cols = payload["feature_cols"]

    for label in LABEL_NAMES:
        plot_label_tree(model, feature_cols, label, OUT_DIR)


if __name__ == "__main__":
    main()
