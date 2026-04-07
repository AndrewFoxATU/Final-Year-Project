# collector_service/collector/system_info_collector.py
# Author: Andrew Fox

import platform
import psutil
import socket
import uuid
import winreg
import pynvml as nvml


class SystemInfoCollector:
    # Collects static host and hardware information. Intended to run once at startup.

    @staticmethod
    def get_system_info():
        hostname = socket.gethostname()
        mac_int = uuid.getnode()
        mac_address = ':'.join(f'{(mac_int >> (8 * i)) & 0xff:02x}' for i in reversed(range(6)))
        gpus = SystemInfoCollector._get_gpu_info()
        vm = psutil.virtual_memory()
        return {
            "host_uuid":       SystemInfoCollector._get_host_uuid(hostname, mac_int),
            "hostname":        hostname,
            "mac_address":     mac_address,
            "os_name":         platform.system(),
            "os_version":      platform.version(),
            "machine":         platform.machine(),
            "cpu_model":       SystemInfoCollector._get_cpu_model(),
            "cpu_core_count":  psutil.cpu_count(logical=False),
            "cpu_thread_count": psutil.cpu_count(logical=True),
            "total_ram_gb":    round(vm.total / (1024 ** 3), 2),
            "gpu_detected":    1 if gpus else 0,
            "gpus":            gpus,
        }

    @staticmethod
    def _get_host_uuid(hostname: str, mac_int: int) -> str:
        """Deterministic UUID based on hostname + MAC address.
        Same machine always produces the same UUID."""
        fingerprint = f"{hostname}-{mac_int}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint))

    @staticmethod
    def _get_cpu_model():
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return name.strip()
        except Exception:
            return platform.processor()

    @staticmethod
    def _get_gpu_info():
        try:
            nvml.nvmlInit()
            count = nvml.nvmlDeviceGetCount()
            gpus = []
            for i in range(count):
                handle = nvml.nvmlDeviceGetHandleByIndex(i)
                gpus.append({
                    "gpu_id":   i,
                    "gpu_uuid": nvml.nvmlDeviceGetUUID(handle),
                    "gpu_name": nvml.nvmlDeviceGetName(handle),
                })
            nvml.nvmlShutdown()
            return gpus
        except Exception:
            return []


# -----------------------------
# Print system info when run directly
# -----------------------------
if __name__ == "__main__":
    data = SystemInfoCollector.get_system_info()
    print("=== System Info ===")
    for key, value in data.items():
        print(f"{key}: {value}")
