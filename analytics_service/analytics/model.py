# analytics_service/analytics/model.py
# Author: Andrew Fox

# Loads the pre-trained Random Forest from model.pkl and exposes a predict() method.
# Takes a feature dict (from features.py), runs inference across all 12 labels,
# and returns component_risks and a list of detected issues ready for the GUI.
# Used by: AnalyticsThread in dashboard_service/gui/main.py

import pickle
from pathlib import Path

from analytics_service.analytics.labels import LABEL_COMPONENTS, LABEL_SEVERITY

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
        probas = self._model.predict_proba([row])

        # probas[i] is shape (1, 2): [prob_no, prob_yes] for label i
        probabilities = {
            label: float(probas[i][0][1])
            for i, label in enumerate(self._label_names)
        }

        issues = [
            label
            for label, fired in zip(self._label_names, predictions)
            if fired
        ]

        # Component risk = highest severity among fired labels for that component (0 if none)
        component_risks = {c: 0 for c in set(LABEL_COMPONENTS.values())}
        for label in issues:
            component = LABEL_COMPONENTS.get(label, "Other")
            component_risks[component] = max(
                component_risks.get(component, 0),
                LABEL_SEVERITY.get(label, 1),
            )

        # Steep exponential penalty curve — low severities barely register,
        # high severities dominate the score:
        #   sev 1 →  2 pts   sev 2 →  5 pts   sev 3 → 15 pts
        #   sev 4 → 35 pts   sev 5 → 60 pts
        # Each penalty is scaled by the model's confidence for that issue.
        _PENALTY = {1: 2, 2: 5, 3: 15, 4: 35, 5: 60}
        penalty = sum(
            _PENALTY.get(LABEL_SEVERITY.get(label, 1), 2) * probabilities.get(label, 1.0)
            for label in issues
        )
        health_score = max(0, min(100, round(100 - penalty)))

        return {
            "issues":          issues,
            "component_risks": component_risks,
            "probabilities":   probabilities,
            "health_score":    health_score,
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
