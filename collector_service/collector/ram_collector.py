# collector_service/collector/ram_collector.py
# Author: Andrew Fox

import psutil
import datetime
import math

class RAMCollector:
    # Collects core RAM and swap data suitable for monitoring and ML analysis.

    @staticmethod
    def get_ram_data():

        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        ram_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_ram_gb": round(vm.total / (1024 ** 3), 2),
            "total_ram_round_gb": math.ceil(vm.total / (1024 ** 3)),
            "used_ram_gb": round(vm.used / (1024 ** 3), 2),
            "ram_usage_percent": vm.percent,
            "swap_usage_percent": swap.percent,
        }

        return ram_data


# -----------------------------
# Print RAM data when run directly
# -----------------------------
if __name__ == "__main__":
    data = RAMCollector.get_ram_data()
    print("=== RAM Data ===")
    for key, value in data.items():
        print(f"{key}: {value}")
