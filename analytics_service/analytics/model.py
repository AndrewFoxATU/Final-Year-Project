# analytics_service/analytics/model.py
# Author: Andrew Fox

# Loads the pre-trained Random Forest from model.pkl and exposes a predict() method.
# Takes a feature dict (from features.py), runs inference across all 12 labels,
# and returns component_risks and a list of detected issues ready for the GUI.
# Used by: AnalyticsThread in dashboard_service/gui/main.py

import pickle
from pathlib import Path

from analytics_service.analytics.labels import LABEL_COMPONENTS

MODEL_PATH = Path("analytics_service/data/model.pkl")


class PerformanceModel:
    # Loads model.pkl once at startup and runs inference on each new feature window.

    def __init__(self):
        with open(MODEL_PATH, "rb") as f:
            payload = pickle.load(f)
        self._model        = payload["model"]
        self._feature_cols = payload["feature_cols"]
        self._label_names  = payload["label_names"]

    def predict(self, features):
        # features: flat dict produced by FeatureExtractor.compute()
        # Returns a dict with:
        #   "issues"          — list of label names that fired
        #   "component_risks" — dict mapping component name to risk level (0-2)

        row = [features.get(col, 0.0) or 0.0 for col in self._feature_cols]
        predictions = self._model.predict([row])[0]

        issues = [
            label
            for label, fired in zip(self._label_names, predictions)
            if fired
        ]

        # Count how many labels fired per component (CPU, RAM, Disk, GPU)
        component_counts = {}
        for label in issues:
            component = LABEL_COMPONENTS.get(label, "Other")
            component_counts[component] = component_counts.get(component, 0) + 1

        # Map count to risk level: 0 = healthy, 1 = warning, 2 = critical
        component_risks = {}
        for component in set(LABEL_COMPONENTS.values()):
            count = component_counts.get(component, 0)
            if count == 0:
                component_risks[component] = 0
            elif count == 1:
                component_risks[component] = 1
            else:
                component_risks[component] = 2

        return {
            "issues":          issues,
            "component_risks": component_risks,
        }


# -----------------------------
# Print a sample prediction when run directly
# -----------------------------
if __name__ == "__main__":
    from analytics_service.analytics.features import FeatureExtractor, WINDOW_SIZE

    # Build a dummy healthy window
    samples = []
    for _ in range(WINDOW_SIZE):
        samples.append({
            "cpu_percent_total":    15.0,
            "freq_current_mhz":     2800.0,
            "ram_usage_percent":    50.0,
            "swap_usage_percent":   5.0,
            "gpu_util_percent":     5.0,
            "gpu_mem_util_percent": 20.0,
            "gpu_temp_c":           55.0,
            "gpu_core_clock_mhz":   300.0,
            "gpu_power_usage_w":    8.0,
            "gpu_power_limit_w":    150.0,
            "avg_read_latency_ms":  2.0,
            "avg_write_latency_ms": 2.0,
            "read_speed_bytes":     0.0,
            "write_speed_bytes":    0.0,
            "disk_usage_percent":   40.0,
        })

    features = FeatureExtractor.compute(samples)
    model = PerformanceModel()
    result = model.predict(features)

    print("Issues detected:", result["issues"] or "None")
    print("Component risks:", result["component_risks"])
