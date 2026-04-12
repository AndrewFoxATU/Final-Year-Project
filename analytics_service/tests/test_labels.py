# analytics_service/tests/test_labels.py
# Author: Andrew Fox
# Run with: python -m pytest analytics_service/tests/test_labels.py -v

import pytest
from analytics_service.analytics.labels import LabelEngine


# -----------------------------
# Shared healthy baseline
# All metrics in normal ranges — no labels should fire
# -----------------------------
HEALTHY = {
    "cpu_percent_total":            20.0,
    "freq_current_mhz":             2800.0,
    "freq_current_mhz_roll_slope":  10.0,
    "ram_usage_percent":            50.0,
    "ram_usage_percent_roll_slope": 0.0,
    "swap_usage_percent":           5.0,
    "swap_usage_percent_roll_slope": 0.0,
    "disk_usage_percent":           40.0,
    "read_speed_bytes":             0.0,
    "write_speed_bytes":            0.0,
    "avg_read_latency_ms":          2.0,
    "avg_write_latency_ms":         2.0,
    "gpu_temp_c":                   55.0,
    "gpu_power_usage_w":            10.0,
    "gpu_power_limit_w":            150.0,
    "gpu_core_clock_mhz_roll_slope": 0.0,
    "gpu_mem_util_percent":         30.0,
    "cpu_percent_total_roll_mean":  20.0,
}


def patch(overrides):
    """Return a copy of HEALTHY with the given overrides applied."""
    f = dict(HEALTHY)
    f.update(overrides)
    return f


# -----------------------------
# Healthy baseline
# -----------------------------
class TestHealthyBaseline:

    def test_no_labels_fire_on_healthy_system(self):
        labels = LabelEngine.apply(HEALTHY)
        for label, value in labels.items():
            assert not value, f"{label} incorrectly fired on healthy baseline"


# -----------------------------
# CPU
# -----------------------------
class TestCPULabels:

    def test_cpu_thermal_throttle_fires(self):
        f = patch({"cpu_percent_total": 80.0, "freq_current_mhz_roll_slope": -200.0})
        assert LabelEngine.apply(f)["cpu_thermal_throttle"]

    def test_cpu_thermal_throttle_no_fire_low_cpu(self):
        f = patch({"cpu_percent_total": 30.0, "freq_current_mhz_roll_slope": -200.0})
        assert not LabelEngine.apply(f)["cpu_thermal_throttle"]

    def test_cpu_thermal_throttle_no_fire_stable_freq(self):
        f = patch({"cpu_percent_total": 80.0, "freq_current_mhz_roll_slope": 10.0})
        assert not LabelEngine.apply(f)["cpu_thermal_throttle"]

    def test_cpu_bottleneck_fires(self):
        f = patch({"cpu_percent_total": 95.0, "ram_usage_percent": 50.0, "disk_usage_percent": 30.0})
        assert LabelEngine.apply(f)["cpu_bottleneck"]

    def test_cpu_bottleneck_no_fire_high_ram(self):
        f = patch({"cpu_percent_total": 95.0, "ram_usage_percent": 80.0, "disk_usage_percent": 30.0})
        assert not LabelEngine.apply(f)["cpu_bottleneck"]

    def test_cpu_sustained_high_load_fires(self):
        f = patch({"cpu_percent_total_roll_mean": 85.0})
        assert LabelEngine.apply(f)["cpu_sustained_high_load"]

    def test_cpu_sustained_high_load_no_fire(self):
        f = patch({"cpu_percent_total_roll_mean": 60.0})
        assert not LabelEngine.apply(f)["cpu_sustained_high_load"]


# -----------------------------
# RAM
# -----------------------------
class TestRAMLabels:

    def test_ram_pressure_fires(self):
        f = patch({"ram_usage_percent": 88.0, "cpu_percent_total": 20.0})
        assert LabelEngine.apply(f)["ram_pressure"]

    def test_ram_pressure_no_fire_high_cpu(self):
        f = patch({"ram_usage_percent": 88.0, "cpu_percent_total": 70.0})
        assert not LabelEngine.apply(f)["ram_pressure"]

    def test_ram_memory_leak_fires(self):
        f = patch({"ram_usage_percent_roll_slope": 0.2, "swap_usage_percent_roll_slope": 0.05})
        assert LabelEngine.apply(f)["ram_memory_leak"]

    def test_ram_memory_leak_no_fire_swap_stable(self):
        f = patch({"ram_usage_percent_roll_slope": 0.2, "swap_usage_percent_roll_slope": 0.0})
        assert not LabelEngine.apply(f)["ram_memory_leak"]

    def test_excessive_swap_fires(self):
        f = patch({"swap_usage_percent": 60.0})
        assert LabelEngine.apply(f)["excessive_swap_usage"]

    def test_excessive_swap_no_fire(self):
        f = patch({"swap_usage_percent": 20.0})
        assert not LabelEngine.apply(f)["excessive_swap_usage"]


# -----------------------------
# Disk
# -----------------------------
class TestDiskLabels:

    def test_disk_full_fires(self):
        f = patch({"disk_usage_percent": 93.0})
        assert LabelEngine.apply(f)["disk_full"]

    def test_disk_full_no_fire(self):
        f = patch({"disk_usage_percent": 75.0})
        assert not LabelEngine.apply(f)["disk_full"]

    def test_disk_bottleneck_fires(self):
        f = patch({"cpu_percent_total": 10.0, "ram_usage_percent": 30.0, "read_speed_bytes": 250_000_000.0})
        assert LabelEngine.apply(f)["disk_bottleneck"]

    def test_disk_bottleneck_no_fire_high_cpu(self):
        f = patch({"cpu_percent_total": 80.0, "ram_usage_percent": 30.0, "read_speed_bytes": 250_000_000.0})
        assert not LabelEngine.apply(f)["disk_bottleneck"]

    def test_disk_high_latency_fires_read(self):
        f = patch({"avg_read_latency_ms": 30.0})
        assert LabelEngine.apply(f)["disk_high_latency"]

    def test_disk_high_latency_fires_write(self):
        f = patch({"avg_write_latency_ms": 30.0})
        assert LabelEngine.apply(f)["disk_high_latency"]

    def test_disk_high_latency_no_fire(self):
        f = patch({"avg_read_latency_ms": 5.0, "avg_write_latency_ms": 5.0})
        assert not LabelEngine.apply(f)["disk_high_latency"]


# -----------------------------
# GPU
# -----------------------------
class TestGPULabels:

    def test_gpu_overheating_fires(self):
        f = patch({"gpu_temp_c": 90.0})
        assert LabelEngine.apply(f)["gpu_overheating"]

    def test_gpu_overheating_no_fire(self):
        f = patch({"gpu_temp_c": 70.0})
        assert not LabelEngine.apply(f)["gpu_overheating"]

    def test_gpu_power_throttle_fires(self):
        f = patch({"gpu_power_usage_w": 148.0, "gpu_power_limit_w": 150.0, "gpu_core_clock_mhz_roll_slope": -10.0})
        assert LabelEngine.apply(f)["gpu_power_throttle"]

    def test_gpu_power_throttle_no_fire_clock_stable(self):
        f = patch({"gpu_power_usage_w": 148.0, "gpu_power_limit_w": 150.0, "gpu_core_clock_mhz_roll_slope": 5.0})
        assert not LabelEngine.apply(f)["gpu_power_throttle"]

    def test_gpu_vram_pressure_fires(self):
        f = patch({"gpu_mem_util_percent": 95.0})
        assert LabelEngine.apply(f)["gpu_vram_pressure"]

    def test_gpu_vram_pressure_no_fire(self):
        f = patch({"gpu_mem_util_percent": 60.0})
        assert not LabelEngine.apply(f)["gpu_vram_pressure"]
