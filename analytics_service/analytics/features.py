# analytics_service/analytics/features.py
# Author: Andrew Fox

# Converts a window of raw telemetry samples (from StorageManager.get_recent_samples)
# into a single flat feature vector ready for ML inference or training.
# Computes rolling statistics (mean, std, slope) over the window for key metrics.
# Used by: generate_training_data.py, collect_real_data.py, model.py

import numpy as np

WINDOW_SIZE = 10

ROLLING_METRICS = [
    "cpu_percent_total",
    "freq_current_mhz",
    "ram_usage_percent",
    "swap_usage_percent",
    "gpu_core_clock_mhz",
    "read_speed_bytes",
    "write_speed_bytes",
]


class FeatureExtractor:
    # Converts a window of raw samples into a flat feature dict for the ML model.

    @staticmethod
    def compute(samples, cpu_max_mhz=None):
        """
        Takes a list of raw sample dicts (newest first, as returned by get_recent_samples).
        cpu_max_mhz: boost-aware max clock from host table (overrides per-sample freq_max_mhz).
        Returns a flat feature dict, or None if there are not enough samples.
        """
        if len(samples) < WINDOW_SIZE:
            return None

        # Work chronologically (oldest first)
        window = list(reversed(samples[:WINDOW_SIZE]))
        latest = window[-1]

        features = {}

        # -----------------------------
        # Point-in-time features
        # -----------------------------
        features["cpu_percent_total"]     = FeatureExtractor._safe(latest, "cpu_percent_total", 0.0)
        features["freq_current_mhz"]      = FeatureExtractor._safe(latest, "freq_current_mhz", 0.0)
        features["freq_max_mhz"]          = float(cpu_max_mhz) if cpu_max_mhz else 0.0
        features["ram_usage_percent"]     = FeatureExtractor._safe(latest, "ram_usage_percent", 0.0)
        features["swap_usage_percent"]    = FeatureExtractor._safe(latest, "swap_usage_percent", 0.0)
        features["gpu_util_percent"]      = FeatureExtractor._safe(latest, "gpu_util_percent", 0.0)
        features["gpu_mem_util_percent"]  = FeatureExtractor._safe(latest, "gpu_mem_util_percent", 0.0)
        features["gpu_temp_c"]            = FeatureExtractor._safe(latest, "gpu_temp_c", 0.0)
        features["gpu_core_clock_mhz"]    = FeatureExtractor._safe(latest, "gpu_core_clock_mhz", 0.0)
        features["gpu_power_usage_w"]     = FeatureExtractor._safe(latest, "gpu_power_usage_w", 0.0)
        features["gpu_power_limit_w"]     = FeatureExtractor._safe(latest, "gpu_power_limit_w", 0.0)
        features["avg_read_latency_ms"]   = FeatureExtractor._safe(latest, "avg_read_latency_ms", 0.0)
        features["avg_write_latency_ms"]  = FeatureExtractor._safe(latest, "avg_write_latency_ms", 0.0)
        features["read_speed_bytes"]      = FeatureExtractor._safe(latest, "read_speed_bytes", 0.0)
        features["write_speed_bytes"]     = FeatureExtractor._safe(latest, "write_speed_bytes", 0.0)
        features["disk_usage_percent"]    = FeatureExtractor._safe(latest, "disk_usage_percent", 0.0)

        # -----------------------------
        # Rolling features
        # -----------------------------
        for metric in ROLLING_METRICS:
            values = [FeatureExtractor._safe(s, metric, 0.0) for s in window]
            features[f"{metric}_roll_mean"]  = float(np.mean(values))
            features[f"{metric}_roll_std"]   = float(np.std(values))
            features[f"{metric}_roll_slope"] = FeatureExtractor._slope(values)

        return features

    @staticmethod
    def _safe(sample, key, default):
        """Returns the value from the sample, or default if missing or None."""
        val = sample.get(key)
        return float(val) if val is not None else default

    @staticmethod
    def _slope(values):
        """Linear regression slope over an evenly spaced window."""
        x = np.arange(len(values), dtype=float)
        y = np.array(values, dtype=float)
        return float(np.polyfit(x, y, 1)[0])


if __name__ == "__main__":
    from storage_service.storage.main import StorageManager
    storage = StorageManager()
    samples = storage.get_recent_samples_all_sessions(WINDOW_SIZE)
    cpu_max_mhz = storage.get_host_cpu_max_mhz()
    features = FeatureExtractor.compute(samples, cpu_max_mhz=cpu_max_mhz)
    if features:
        print("=== Feature Vector ===")
        for key, value in features.items():
            print(f"{key}: {value:.4f}")
    else:
        print(f"Not enough samples (need {WINDOW_SIZE})")
    storage.close()
