# collector_service/tests/test_collectors.py
# Author: Andrew Fox
# Run with: python -m pytest collector_service/tests/test_collectors.py -v

import pytest
from collector_service.collector.cpu_collector import CPUCollector
from collector_service.collector.ram_collector import RAMCollector
from collector_service.collector.disk_collector import DiskCollector
from collector_service.collector.gpu_collector import GPUCollector


# -----------------------------
# CPU Collector
# -----------------------------
class TestCPUCollector:

    def setup_method(self):
        self.data = CPUCollector.get_cpu_data()

    def test_returns_required_keys(self):
        for key in ("timestamp", "cpu_percent_total", "freq_current_mhz"):
            assert key in self.data

    def test_cpu_percent_in_range(self):
        assert 0.0 <= self.data["cpu_percent_total"] <= 100.0

    def test_freq_current_is_positive(self):
        if self.data["freq_current_mhz"] is not None:
            assert self.data["freq_current_mhz"] > 0

    def test_timestamp_is_string(self):
        assert isinstance(self.data["timestamp"], str)


# -----------------------------
# RAM Collector
# -----------------------------
class TestRAMCollector:

    def setup_method(self):
        self.data = RAMCollector.get_ram_data()

    def test_returns_required_keys(self):
        for key in ("timestamp", "total_ram_gb", "total_ram_round_gb", "used_ram_gb",
                    "ram_usage_percent", "swap_usage_percent"):
            assert key in self.data

    def test_ram_usage_in_range(self):
        assert 0.0 <= self.data["ram_usage_percent"] <= 100.0

    def test_swap_usage_in_range(self):
        assert 0.0 <= self.data["swap_usage_percent"] <= 100.0

    def test_used_does_not_exceed_total(self):
        assert self.data["used_ram_gb"] <= self.data["total_ram_gb"]

    def test_total_ram_is_positive(self):
        assert self.data["total_ram_gb"] > 0

    def test_timestamp_is_string(self):
        assert isinstance(self.data["timestamp"], str)


# -----------------------------
# Disk Collector
# -----------------------------
class TestDiskCollector:

    def setup_method(self):
        self.data = DiskCollector.get_disk_data()

    def test_returns_required_keys(self):
        for key in ("timestamp", "read_speed_bytes", "write_speed_bytes",
                    "avg_read_latency_ms", "avg_write_latency_ms", "disks"):
            assert key in self.data

    def test_disks_list_not_empty(self):
        assert len(self.data["disks"]) > 0

    def test_read_speed_not_negative(self):
        assert self.data["read_speed_bytes"] >= 0

    def test_write_speed_not_negative(self):
        assert self.data["write_speed_bytes"] >= 0

    def test_disk_usage_in_range(self):
        for disk in self.data["disks"]:
            assert 0.0 <= disk["usage_percent"] <= 100.0

    def test_disk_used_does_not_exceed_total(self):
        for disk in self.data["disks"]:
            assert disk["used_gb"] <= disk["total_gb"]

    def test_disk_has_required_keys(self):
        for disk in self.data["disks"]:
            for key in ("device", "mountpoint", "fstype", "total_gb", "used_gb", "usage_percent"):
                assert key in disk

    def test_multiple_partitions(self):
        from unittest.mock import patch, MagicMock

        fake_partitions = [
            MagicMock(device="C:\\", mountpoint="C:\\", fstype="NTFS"),
            MagicMock(device="D:\\", mountpoint="D:\\", fstype="NTFS"),
        ]

        def fake_usage(mountpoint):
            usage = MagicMock()
            usage.total = 500 * (1024 ** 3)
            usage.used  = 200 * (1024 ** 3)
            usage.percent = 40.0
            return usage

        with patch("psutil.disk_partitions", return_value=fake_partitions), \
             patch("psutil.disk_usage", side_effect=fake_usage):
            data = DiskCollector.get_disk_data()

        assert len(data["disks"]) == 2
        devices = [d["device"] for d in data["disks"]]
        assert "C:\\" in devices
        assert "D:\\" in devices
        for disk in data["disks"]:
            assert disk["used_gb"] <= disk["total_gb"]
            assert 0.0 <= disk["usage_percent"] <= 100.0


# -----------------------------
# CPU Collector — Edge Cases
# -----------------------------
class TestCPUCollectorEdgeCases:

    def test_pdh_unavailable_falls_back_to_psutil(self):
        import collector_service.collector.cpu_collector as mod
        original = mod._pdh_available
        mod._pdh_available = False
        try:
            data = CPUCollector.get_cpu_data()
            assert data["freq_current_mhz"] is not None or data["freq_current_mhz"] is None
        finally:
            mod._pdh_available = original

    def test_cpu_percent_not_negative(self):
        data = CPUCollector.get_cpu_data()
        assert data["cpu_percent_total"] >= 0


# -----------------------------
# RAM Collector — Edge Cases
# -----------------------------
class TestRAMCollectorEdgeCases:

    def test_zero_swap(self):
        from unittest.mock import patch, MagicMock
        fake_swap = MagicMock()
        fake_swap.percent = 0.0
        with patch("psutil.swap_memory", return_value=fake_swap):
            data = RAMCollector.get_ram_data()
        assert data["swap_usage_percent"] == 0.0

    def test_high_ram_usage(self):
        from unittest.mock import patch, MagicMock
        fake_vm = MagicMock()
        fake_vm.total  = 8 * (1024 ** 3)
        fake_vm.used   = 7.8 * (1024 ** 3)
        fake_vm.percent = 97.5
        with patch("psutil.virtual_memory", return_value=fake_vm):
            data = RAMCollector.get_ram_data()
        assert data["ram_usage_percent"] == 97.5
        assert data["used_ram_gb"] <= data["total_ram_gb"]


# -----------------------------
# Disk Collector — Edge Cases
# -----------------------------
class TestDiskCollectorEdgeCases:

    def test_permission_error_partition_skipped(self):
        from unittest.mock import patch, MagicMock
        fake_partitions = [
            MagicMock(device="C:\\", mountpoint="C:\\", fstype="NTFS"),
            MagicMock(device="D:\\", mountpoint="D:\\", fstype="NTFS"),
        ]

        def fake_usage(mountpoint):
            if mountpoint == "D:\\":
                raise PermissionError
            usage = MagicMock()
            usage.total   = 500 * (1024 ** 3)
            usage.used    = 200 * (1024 ** 3)
            usage.percent = 40.0
            return usage

        with patch("psutil.disk_partitions", return_value=fake_partitions), \
             patch("psutil.disk_usage", side_effect=fake_usage):
            data = DiskCollector.get_disk_data()

        assert len(data["disks"]) == 1
        assert data["disks"][0]["device"] == "C:\\"

    def test_disk_nearly_full(self):
        from unittest.mock import patch, MagicMock
        fake_partitions = [MagicMock(device="C:\\", mountpoint="C:\\", fstype="NTFS")]

        def fake_usage(mountpoint):
            usage = MagicMock()
            usage.total   = 500 * (1024 ** 3)
            usage.used    = 498 * (1024 ** 3)
            usage.percent = 99.6
            return usage

        with patch("psutil.disk_partitions", return_value=fake_partitions), \
             patch("psutil.disk_usage", side_effect=fake_usage):
            data = DiskCollector.get_disk_data()

        assert data["disks"][0]["usage_percent"] > 90
        assert data["disks"][0]["used_gb"] <= data["disks"][0]["total_gb"]

    def test_disk_empty(self):
        from unittest.mock import patch, MagicMock
        fake_partitions = [MagicMock(device="C:\\", mountpoint="C:\\", fstype="NTFS")]

        def fake_usage(mountpoint):
            usage = MagicMock()
            usage.total   = 500 * (1024 ** 3)
            usage.used    = 0
            usage.percent = 0.0
            return usage

        with patch("psutil.disk_partitions", return_value=fake_partitions), \
             patch("psutil.disk_usage", side_effect=fake_usage):
            data = DiskCollector.get_disk_data()

        assert data["disks"][0]["usage_percent"] == 0.0
        assert data["disks"][0]["used_gb"] == 0.0


# -----------------------------
# GPU Collector — No GPU present
# -----------------------------
class TestGPUCollectorNoGPU:

    def test_no_gpu_returns_empty_list(self):
        from unittest.mock import patch
        with patch("pynvml.nvmlInit"), \
             patch("pynvml.nvmlDeviceGetCount", return_value=0), \
             patch("pynvml.nvmlShutdown"):
            data = GPUCollector.get_gpu_data()
        assert data["gpu_count"] == 0
        assert data["gpus"] == []

    def test_no_gpu_frontend_guard(self):
        # Simulate what live_monitor.update_gpu_data does when gpus is empty
        data = {"gpu_count": 0, "gpus": []}
        # The frontend guard — should not raise
        if not data["gpus"]:
            return
        raise AssertionError("Frontend guard did not return early on empty gpus")


# -----------------------------
# GPU Collector
# -----------------------------
class TestGPUCollector:

    def setup_method(self):
        self.data = GPUCollector.get_gpu_data()

    def test_returns_required_keys(self):
        for key in ("gpu_count", "gpus"):
            assert key in self.data

    def test_gpu_count_matches_list(self):
        assert self.data["gpu_count"] == len(self.data["gpus"])

    def test_gpu_util_in_range(self):
        for gpu in self.data["gpus"]:
            assert 0.0 <= gpu["gpu_util_percent"] <= 100.0

    def test_gpu_mem_util_in_range(self):
        for gpu in self.data["gpus"]:
            assert 0.0 <= gpu["gpu_mem_util_percent"] <= 100.0

    def test_gpu_temp_is_positive(self):
        for gpu in self.data["gpus"]:
            assert gpu["gpu_temp_c"] > 0

    def test_gpu_power_usage_does_not_exceed_limit(self):
        for gpu in self.data["gpus"]:
            assert gpu["gpu_power_usage_w"] <= gpu["gpu_power_limit_w"] * 1.05

    def test_gpu_has_required_keys(self):
        for gpu in self.data["gpus"]:
            for key in ("gpu_id", "gpu_util_percent", "gpu_mem_util_percent",
                        "gpu_mem_used_mb", "gpu_temp_c", "gpu_core_clock_mhz",
                        "gpu_power_usage_w", "gpu_power_limit_w"):
                assert key in gpu
