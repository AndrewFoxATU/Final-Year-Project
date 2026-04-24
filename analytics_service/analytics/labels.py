# analytics_service/analytics/labels.py
# Author: Andrew Fox

# Applies 12 rule-based boolean labels to a feature dict produced by features.py.
# Each rule is a set of conditions based on known thresholds for what counts as an issue.
# Used by: generate_training_data.py, collect_real_data.py


# -----------------------------
# Label Definitions
# Maps each label to its component for grouping in the GUI
# -----------------------------
LABEL_COMPONENTS = {
    "cpu_thermal_throttle":    "CPU",
    "cpu_bottleneck":          "CPU",
    "cpu_sustained_high_load": "CPU",
    "ram_pressure":            "RAM",
    "ram_memory_leak":         "RAM",
    "excessive_swap_usage":    "RAM",
    "disk_full":               "Disk",
    "disk_bottleneck":         "Disk",
    "disk_high_latency":       "Disk",
    "gpu_overheating":         "GPU",
    "gpu_power_throttle":      "GPU",
    "gpu_vram_pressure":       "GPU",
}

LABEL_NAMES = list(LABEL_COMPONENTS.keys())

# Severity of each issue on a 1–5 scale:
#   5 = critical  (hardware damage / total failure imminent)
#   4 = serious   (will cause system crash or hardware risk without intervention)
#   3 = warning   (significant performance impact or resource exhaustion approaching)
#   2 = minor     (elevated load, worth monitoring but not immediately harmful)
#   1 = info      (informational only)
LABEL_SEVERITY = {
    "cpu_thermal_throttle":    4,  # hardware damage risk, frequency actively dropping
    "cpu_bottleneck":          3,  # CPU is the hard constraint on the whole system
    "cpu_sustained_high_load": 2,  # high but not yet bottlenecking or throttling
    "ram_pressure":            3,  # apps may start OOM-crashing soon
    "ram_memory_leak":         4,  # will exhaust memory entirely; requires restart
    "excessive_swap_usage":    3,  # system is swapping heavily, major perf hit
    "disk_full":               4,  # writes will fail; data loss / crash risk (recoverable)
    "disk_bottleneck":         2,  # high I/O throughput but no hardware risk
    "disk_high_latency":       3,  # slow I/O, cascading delays across the system
    "gpu_overheating":         5,  # GPU may throttle, shut down, or be damaged
    "gpu_power_throttle":      3,  # GPU clock actively dropping due to power cap
    "gpu_vram_pressure":       3,  # VRAM nearly full, GPU OOM errors likely
}


class LabelEngine:
    # Applies domain-knowledge rules to a feature dict to produce 12 boolean labels.

    @staticmethod
    def apply(features):
        """
        Takes a feature dict from FeatureExtractor.compute().
        Returns a dict of 12 boolean labels.
        """
        f = features

        labels = {}

        # -----------------------------
        # CPU
        # -----------------------------

        # Thermal throttle: high CPU load AND frequency actively dropping
        labels["cpu_thermal_throttle"] = (
            f["cpu_percent_total"] > 70 and
            f["freq_current_mhz_roll_slope"] < -50
        )

        # Bottleneck: CPU maxed out but RAM and disk are fine (CPU is the constraint)
        labels["cpu_bottleneck"] = (
            f["cpu_percent_total"] > 90 and
            f["ram_usage_percent"] < 70 and
            f["disk_usage_percent"] < 50
        )

        # Sustained high load: CPU has been consistently high over the window
        labels["cpu_sustained_high_load"] = (
            f["cpu_percent_total_roll_mean"] > 88
        )

        # -----------------------------
        # RAM
        # -----------------------------

        # RAM pressure: memory nearly full but CPU is not the cause
        labels["ram_pressure"] = (
            f["ram_usage_percent"] > 80 and
            f["cpu_percent_total"] < 50
        )

        # Memory leak: RAM and swap both steadily rising over the window
        labels["ram_memory_leak"] = (
            f["ram_usage_percent_roll_slope"] > 0.3 and
            f["swap_usage_percent_roll_slope"] > 0.05
        )

        # Excessive swap: system is heavily using swap space
        labels["excessive_swap_usage"] = (
            f["swap_usage_percent"] > 50
        )

        # -----------------------------
        # Disk
        # -----------------------------

        # Disk full: partition nearly out of space
        labels["disk_full"] = (
            f["disk_usage_percent"] > 90
        )

        # Disk bottleneck: high disk throughput while CPU and RAM are idle
        labels["disk_bottleneck"] = (
            f["cpu_percent_total"] < 40 and
            f["ram_usage_percent"] < 60 and
            (f["read_speed_bytes"] > 200_000_000 or f["write_speed_bytes"] > 200_000_000)
        )

        # High latency: slow read or write response times
        labels["disk_high_latency"] = (
            f["avg_read_latency_ms"] > 20 or
            f["avg_write_latency_ms"] > 20
        )

        # -----------------------------
        # GPU
        # -----------------------------

        # Overheating: GPU temperature dangerously high
        labels["gpu_overheating"] = (
            f["gpu_temp_c"] > 85
        )

        # Power throttle: GPU hitting power limit AND clock speed dropping
        labels["gpu_power_throttle"] = (
            f["gpu_power_usage_w"] >= f["gpu_power_limit_w"] * 0.98 and
            f["gpu_core_clock_mhz_roll_slope"] < -5
        )

        # VRAM pressure: GPU memory nearly full
        labels["gpu_vram_pressure"] = (
            f["gpu_mem_util_percent"] > 90
        )

        return labels


# -----------------------------
# Print labels when run directly
# -----------------------------
if __name__ == "__main__":
    from storage_service.storage.main import StorageManager
    from analytics_service.analytics.features import FeatureExtractor, WINDOW_SIZE

    storage = StorageManager()
    samples = storage.get_recent_samples_all_sessions(WINDOW_SIZE)
    features = FeatureExtractor.compute(samples)

    if features:
        labels = LabelEngine.apply(features)
        print("=== Labels ===")
        for label, value in labels.items():
            status = "YES" if value else "no"
            print(f"  {label:<30} {status}")
    else:
        print(f"Not enough samples (need {WINDOW_SIZE})")

    storage.close()
