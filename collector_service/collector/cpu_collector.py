# collector_service/collector/cpu_collector.py
# Author: Andrew Fox

import psutil
import datetime

class CPUCollector:
     # Collects raw CPU data suitable for logging and ML analysis.

    @staticmethod
    def get_cpu_data():
        freq = psutil.cpu_freq()

        cpu_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu_percent_total": psutil.cpu_percent(interval=None),
            "freq_current_mhz": freq.current if freq else None,
            "freq_max_mhz": freq.max if freq else None,
        }
        return cpu_data

# -----------------------------
# Print CPU data when run directly
# -----------------------------
if __name__ == "__main__":
    data = CPUCollector.get_cpu_data()
    print("=== Raw CPU Data ===")
    for key, value in data.items():
        print(f"{key}: {value}")
