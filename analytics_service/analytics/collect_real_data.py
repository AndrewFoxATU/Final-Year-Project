# analytics_service/analytics/collect_real_data.py
# Author: Andrew Fox

# Reads one or more telemetry .db files, computes features and labels for each
# rolling window of samples, and appends the resulting rows to training_data.csv.
# Existing synthetic rows in the CSV are preserved.

# Usage: python -m analytics_service.analytics.collect_real_data

import csv
import sqlite3
from pathlib import Path

from analytics_service.analytics.features import FeatureExtractor, WINDOW_SIZE
from analytics_service.analytics.labels import LabelEngine, LABEL_NAMES

OUTPUT_PATH = Path("analytics_service/data/training_data.csv")

DB_FILES = [
    "telemetry.db",
    "telemetry-2.db",
    "telemetry-cathal.db",
    "telemetry-andrew-pc.db",
]


def fetch_sessions(conn):
    return [
        row[0]
        for row in conn.execute("SELECT session_id FROM session").fetchall()
    ]



def process_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    host = conn.execute("SELECT hostname FROM host LIMIT 1").fetchone()
    hostname = host["hostname"] if host else db_path

    sessions = fetch_sessions(conn)
    rows = []

    for sid in sessions:
        samples = conn.execute('''
            SELECT s.sample_id,
                   c.cpu_percent_total, c.freq_current_mhz,
                   r.ram_usage_percent, r.swap_usage_percent,
                   di.read_speed_bytes, di.write_speed_bytes,
                   di.avg_read_latency_ms, di.avg_write_latency_ms,
                   MAX(dp.usage_percent) AS disk_usage_percent,
                   g.gpu_util_percent, g.gpu_mem_util_percent,
                   g.gpu_temp_c, g.gpu_core_clock_mhz,
                   g.gpu_power_usage_w, g.gpu_power_limit_w
            FROM sample s
            JOIN cpu_sample c ON c.sample_id = s.sample_id
            JOIN ram_sample r ON r.sample_id = s.sample_id
            JOIN disk_io_sample di ON di.sample_id = s.sample_id
            JOIN disk_partition_sample dp ON dp.sample_id = s.sample_id
            LEFT JOIN gpu_sample g ON g.sample_id = s.sample_id AND g.gpu_id = 0
            WHERE s.session_id = ?
            GROUP BY s.sample_id
            ORDER BY s.sample_id ASC
        ''', (sid,)).fetchall()

        samples = [dict(r) for r in samples]

        for i in range(len(samples) - WINDOW_SIZE + 1):
            window = list(reversed(samples[i:i + WINDOW_SIZE]))
            features = FeatureExtractor.compute(window)
            if features is None:
                continue
            labels = LabelEngine.apply(features)
            row = {**features}
            for label in LABEL_NAMES:
                row[label] = 1 if labels[label] else 0
            row["source"] = "real"
            rows.append(row)

    conn.close()
    return hostname, rows


def collect():
    # Load existing CSV to preserve synthetic rows and get fieldnames
    existing_rows = []
    fieldnames = None

    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            existing_rows = [r for r in reader if r.get("source") == "synthetic"]

    new_rows = []
    for db_file in DB_FILES:
        path = Path(db_file)
        if not path.exists():
            print(f"  Skipping {db_file} (not found)")
            continue
        hostname, rows = process_db(str(path))
        print(f"  {db_file} ({hostname}): {len(rows)} windows")
        new_rows.extend(rows)

    if not new_rows:
        print("No real data found.")
        return

    if fieldnames is None:
        fieldnames = list(new_rows[0].keys())

    all_rows = existing_rows + new_rows

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSynthetic rows kept: {len(existing_rows)}")
    print(f"Real rows added:     {len(new_rows)}")
    print(f"Total rows:          {len(all_rows)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    print("Collecting real telemetry data...")
    collect()
