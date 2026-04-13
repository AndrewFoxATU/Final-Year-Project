# analytics_service/analytics/generate_training_data.py
# Author: Andrew Fox

# Generates a synthetic labelled training dataset covering all 12 issue types.
# Each scenario constructs a window of realistic raw metric samples with controlled
# values and noise, computes features via features.py, applies labels via labels.py,
# and appends the result to training_data.csv.
# Run directly by the developer before shipping the model.

# Usage: python -m analytics_service.analytics.generate_training_data

import csv
import random
import numpy as np
from pathlib import Path

from analytics_service.analytics.features import FeatureExtractor, WINDOW_SIZE
from analytics_service.analytics.labels import LabelEngine, LABEL_NAMES

OUTPUT_PATH = Path("analytics_service/data/training_data.csv")
SAMPLES_PER_SCENARIO = 500


# -----------------------------
# Noise helper
# -----------------------------
def jitter(value, pct=0.05):
    """Add small random noise to a value."""
    return value + value * random.uniform(-pct, pct)


# -----------------------------
# Window builder
# Build a window of raw sample dicts with realistic values for a scenario
# -----------------------------
def build_window(overrides_fn):
    """
    Calls overrides_fn(i) for each of WINDOW_SIZE steps to get per-step values.
    Returns a list of raw sample dicts (oldest first).
    """
    window = []
    for i in range(WINDOW_SIZE):
        base = overrides_fn(i)
        sample = {
            "cpu_percent_total":    base.get("cpu_percent_total",    jitter(15.0)),
            "freq_current_mhz":     base.get("freq_current_mhz",     jitter(2800.0)),
            "ram_usage_percent":    base.get("ram_usage_percent",     jitter(50.0)),
            "swap_usage_percent":   base.get("swap_usage_percent",    jitter(5.0)),
            "gpu_util_percent":     base.get("gpu_util_percent",      jitter(5.0)),
            "gpu_mem_util_percent": base.get("gpu_mem_util_percent",  jitter(20.0)),
            "gpu_temp_c":           base.get("gpu_temp_c",            jitter(55.0)),
            "gpu_core_clock_mhz":   base.get("gpu_core_clock_mhz",   jitter(300.0)),
            "gpu_power_usage_w":    base.get("gpu_power_usage_w",     jitter(8.0)),
            "gpu_power_limit_w":    base.get("gpu_power_limit_w",     150.0),
            "avg_read_latency_ms":  base.get("avg_read_latency_ms",   jitter(2.0)),
            "avg_write_latency_ms": base.get("avg_write_latency_ms",  jitter(2.0)),
            "read_speed_bytes":     base.get("read_speed_bytes",      0.0),
            "write_speed_bytes":    base.get("write_speed_bytes",     0.0),
            "disk_usage_percent":   base.get("disk_usage_percent",    jitter(40.0)),
        }
        window.append(sample)
    # Return newest first (as get_recent_samples returns)
    return list(reversed(window))


# -----------------------------
# Scenario definitions
# Each returns a function that builds per-step overrides
# -----------------------------
def scenario_healthy():
    def fn(_):
        return {}
    return fn


def scenario_cpu_thermal_throttle():
    def fn(i):
        return {
            "cpu_percent_total":  jitter(85.0, 0.05),
            "freq_current_mhz":   3200.0 - i * 180 + random.uniform(-50, 50),
        }
    return fn


def scenario_cpu_bottleneck():
    def fn(i):
        return {
            "cpu_percent_total":  jitter(95.0, 0.03),
            "ram_usage_percent":  jitter(45.0, 0.05),
            "disk_usage_percent": jitter(30.0, 0.05),
        }
    return fn


def scenario_cpu_sustained_high_load():
    def fn(i):
        return {
            "cpu_percent_total": jitter(88.0, 0.05),
        }
    return fn


def scenario_ram_pressure():
    def fn(i):
        return {
            "ram_usage_percent":  jitter(87.0, 0.03),
            "cpu_percent_total":  jitter(20.0, 0.1),
        }
    return fn


def scenario_ram_memory_leak():
    def fn(i):
        return {
            "ram_usage_percent":  45.0 + i * 0.5 + random.uniform(-0.1, 0.1),
            "swap_usage_percent": 5.0 + i * 0.1 + random.uniform(-0.02, 0.02),
        }
    return fn


def scenario_excessive_swap():
    def fn(i):
        return {
            "swap_usage_percent": jitter(60.0, 0.05),
        }
    return fn


def scenario_disk_full():
    def fn(i):
        return {
            "disk_usage_percent": jitter(93.0, 0.02),
        }
    return fn


def scenario_disk_bottleneck():
    def fn(i):
        return {
            "cpu_percent_total":  jitter(10.0, 0.1),
            "ram_usage_percent":  jitter(30.0, 0.05),
            "read_speed_bytes":   jitter(250_000_000.0, 0.1),
        }
    return fn


def scenario_disk_high_latency():
    def fn(i):
        return {
            "avg_read_latency_ms":  jitter(35.0, 0.1),
            "avg_write_latency_ms": jitter(30.0, 0.1),
        }
    return fn


def scenario_gpu_overheating():
    def fn(i):
        return {
            "gpu_temp_c":          jitter(90.0, 0.03),
            "gpu_util_percent":    jitter(95.0, 0.05),
            "gpu_power_usage_w":   jitter(100.0, 0.1),
        }
    return fn


def scenario_gpu_power_throttle():
    def fn(i):
        return {
            "gpu_power_usage_w":          jitter(149.5, 0.003),
            "gpu_power_limit_w":          150.0,
            "gpu_core_clock_mhz":         1800.0 - i * 20 + random.uniform(-10, 10),
            "gpu_util_percent":           jitter(98.0, 0.02),
        }
    return fn


def scenario_gpu_vram_pressure():
    def fn(i):
        return {
            "gpu_mem_util_percent": jitter(93.0, 0.03),
            "gpu_util_percent":     jitter(80.0, 0.05),
        }
    return fn


# Scenarios with no real telemetry examples get more synthetic rows
# to compensate. Scenarios well-represented in real data keep 500.
SCENARIOS = [
    (scenario_healthy,                500),
    (scenario_cpu_thermal_throttle,   800),
    (scenario_cpu_bottleneck,         500),
    (scenario_cpu_sustained_high_load, 500),
    (scenario_ram_pressure,           800),
    (scenario_ram_memory_leak,        800),
    (scenario_excessive_swap,         800),
    (scenario_disk_full,              500),
    (scenario_disk_bottleneck,        500),
    (scenario_disk_high_latency,      800),
    (scenario_gpu_overheating,        800),
    (scenario_gpu_power_throttle,     800),
    (scenario_gpu_vram_pressure,      800),
]


# -----------------------------
# Main
# -----------------------------
def generate():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    feature_keys = None
    rows = []

    for scenario_fn, n_samples in SCENARIOS:
        name = scenario_fn.__name__.replace("scenario_", "")
        count = 0

        for _ in range(n_samples):
            window = build_window(scenario_fn())
            features = FeatureExtractor.compute(window)
            if features is None:
                continue

            labels = LabelEngine.apply(features)

            if feature_keys is None:
                feature_keys = list(features.keys())

            row = {**features}
            for label in LABEL_NAMES:
                row[label] = 1 if labels[label] else 0
            row["source"] = "synthetic"
            rows.append(row)
            count += 1

        print(f"  {name:<30} {count} rows")

    # Write CSV
    fieldnames = feature_keys + LABEL_NAMES + ["source"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    print("Generating synthetic training data...")
    generate()
