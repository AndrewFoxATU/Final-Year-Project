# analytics_service/visualisations/plot_training_breakdown.py
# Author: Andrew Fox

# Bar chart showing the sample count per telemetry source (db file + synthetic).
# Synthetic count is read from training_data.csv.
# Real counts are derived by querying each db file directly.
# Usage: python -m analytics_service.visualisations.plot_training_breakdown

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

from analytics_service.analytics.features import WINDOW_SIZE

DATA_PATH = Path("analytics_service/data/training_data.csv")
OUT_PATH  = Path("analytics_service/visualisations/data_training_breakdown.png")

DB_FILES = [
    "telemetry.db",
    "telemetry-2.db",
    "telemetry-cathal.db",
    "telemetry-andrew-pc.db",
]


def count_windows(db_path):
    """Return (hostname, window_count) for a db file."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    host = conn.execute("SELECT hostname FROM host LIMIT 1").fetchone()
    hostname = host["hostname"] if host else db_path
    sessions = [r[0] for r in conn.execute("SELECT session_id FROM session").fetchall()]
    total = 0
    for sid in sessions:
        n = conn.execute(
            "SELECT COUNT(*) FROM sample WHERE session_id = ?", (sid,)
        ).fetchone()[0]
        total += max(0, n - WINDOW_SIZE + 1)
    conn.close()
    return hostname, total


def main():
    df = pd.read_csv(DATA_PATH)
    synthetic_count = int((df["source"] == "synthetic").sum())

    labels = [f"Synthetic\n(generated)"]
    values = [synthetic_count]
    colours = ["coral"]

    for db_file in DB_FILES:
        path = Path(db_file)
        if not path.exists():
            print(f"  Skipping {db_file} (not found)")
            continue
        hostname, count = count_windows(str(path))
        labels.append(f"{hostname}\n({db_file})")
        values.append(count)
        colours.append("steelblue")

    total = sum(values)

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(labels, values, color=colours)

    ax.set_ylabel("Windows (rows)")
    ax.set_title(f"Training data sources — {total:,} total rows")
    ax.set_ylim(0, max(values) * 1.15)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 80,
                str(val), ha="center", va="bottom", fontsize=10, fontweight="bold")

    synthetic_patch = mpatches.Patch(color="coral",     label="Synthetic")
    real_patch      = mpatches.Patch(color="steelblue", label="Real telemetry")
    ax.legend(handles=[synthetic_patch, real_patch])

    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved {OUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
