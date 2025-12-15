# collector_service/collector/gpu_collector.py
# Author: Andrew Fox

import datetime
import pynvml as nvml


class GPUCollector:
    # Collects raw GPU data suitable for logging and ML analysis.

    @staticmethod
    def get_gpu_data():
        nvml.nvmlInit()

        gpu_count = nvml.nvmlDeviceGetCount()
        timestamp = datetime.datetime.now().isoformat()

        gpus = []

        for i in range(gpu_count):
            handle = nvml.nvmlDeviceGetHandleByIndex(i)

            util = nvml.nvmlDeviceGetUtilizationRates(handle)
            mem = nvml.nvmlDeviceGetMemoryInfo(handle)

            gpu_data = {
                "timestamp": timestamp,
                "gpu_id": i,
                "gpu_name": nvml.nvmlDeviceGetName(handle),
                "gpu_uuid": nvml.nvmlDeviceGetUUID(handle),

                "gpu_util_percent": util.gpu,
                "gpu_mem_util_percent": util.memory,

                "gpu_mem_total_mb": mem.total // (1024 * 1024),
                "gpu_mem_used_mb": mem.used // (1024 * 1024),
                "gpu_mem_free_mb": mem.free // (1024 * 1024),

                "gpu_temp_c": nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU),

                "gpu_core_clock_mhz": nvml.nvmlDeviceGetClockInfo(handle, nvml.NVML_CLOCK_GRAPHICS),
                "gpu_mem_clock_mhz": nvml.nvmlDeviceGetClockInfo( handle, nvml.NVML_CLOCK_MEM),

                "gpu_power_usage_w": nvml.nvmlDeviceGetPowerUsage(handle) / 1000,
                "gpu_power_limit_w": nvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000,

                "gpu_pcie_rx_mb": nvml.nvmlDeviceGetPcieThroughput(handle, nvml.NVML_PCIE_UTIL_RX_BYTES),
                "gpu_pcie_tx_mb": nvml.nvmlDeviceGetPcieThroughput(handle, nvml.NVML_PCIE_UTIL_TX_BYTES),
            }

            gpus.append(gpu_data)

        nvml.nvmlShutdown()

        return {
            "gpu_count": gpu_count,
            "gpus": gpus
        }


# -----------------------------
# Print GPU data when run directly
# -----------------------------
if __name__ == "__main__":
    data = GPUCollector.get_gpu_data()
    print("=== Raw GPU Data ===")
    for key, value in data.items():
        print(f"{key}: {value}")
