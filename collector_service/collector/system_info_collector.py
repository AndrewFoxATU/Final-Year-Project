# collector_service/collector/system_info_collector.py
# Author: Andrew Fox

import platform
import socket
import winreg
import pynvml as nvml


class SystemInfoCollector:
    # Collects static host and hardware information. Intended to run once at startup.

    @staticmethod
    def get_system_info():
        return {
            "hostname":   socket.gethostname(),
            "os_name":    platform.system(),
            "os_version": platform.version(),
            "machine":    platform.machine(),
            "cpu_model":  SystemInfoCollector._get_cpu_model(),
            "gpus":       SystemInfoCollector._get_gpu_info(),
        }

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
