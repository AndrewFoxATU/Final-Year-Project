# collector_service/collector/ram_collector.py
# Author: Andrew Fox

import psutil
import datetime
import math

class RAMCollector:
    """Collects core RAM and swap data suitable for monitoring and ML analysis."""

    @staticmethod
    def get_ram_data():

        ram_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            # Precise total RAM for ML/testing
            "total_ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
            # Display-friendly rounded-up total RAM
            "total_ram_round_gb": math.ceil(psutil.virtual_memory().total / (1024 ** 3)),
            "used_ram_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
            "available_ram_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
            "ram_usage_percent": psutil.virtual_memory().percent,
            "swap_total_gb": round(psutil.swap_memory().total / (1024 ** 3), 2),
            "swap_used_gb": round(psutil.swap_memory().used / (1024 ** 3), 2),
            "swap_usage_percent": psutil.swap_memory().percent,
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
