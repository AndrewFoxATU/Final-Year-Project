# collector_service/collector/cpu_collector.py
# Author: Andrew Fox

import psutil
import datetime


class CPUCollector:
    # Collects raw CPU data suitable for logging and ML analysis.


    @staticmethod
    def get_cpu_data():

        cpu_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu_percent_total": psutil.cpu_percent(interval=0.5),
            "cpu_percent_per_core": psutil.cpu_percent(interval=0.5, percpu=True),
            "cpu_thread_count": psutil.cpu_count(logical=True),
            "cpu_core_count": psutil.cpu_count(logical=False),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            "cpu_times_per_core": [t._asdict() for t in psutil.cpu_times(percpu=True)],
            "cpu_stats": psutil.cpu_stats()._asdict(),
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
