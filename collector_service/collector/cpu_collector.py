# collector_service/collector/cpu_collector.py
# Author: Andrew Fox

import win32pdh
import psutil
import datetime

# Open the PDH query once at import time.
# psutil.cpu_freq() on Windows returns the base P-state clock for both
# current and max via NtPowerInformation — it cannot reflect turbo boost.
# '\Processor Information(_Total)\Actual Frequency' reads directly from
# hardware and returns the true real-time frequency including turbo boost.
try:
    _pdh_query = win32pdh.OpenQuery()
    _pdh_freq_counter = win32pdh.AddCounter(
        _pdh_query,
        r"\Processor Information(_Total)\Actual Frequency"
    )
    win32pdh.CollectQueryData(_pdh_query)  # seed — real value available next call
    _pdh_available = True
except Exception:
    _pdh_available = False


class CPUCollector:
    # Collects raw CPU data suitable for logging and ML analysis.

    @staticmethod
    def get_cpu_data():
        freq = psutil.cpu_freq(percpu=False)

        if _pdh_available:
            win32pdh.CollectQueryData(_pdh_query)
            _, freq_current = win32pdh.GetFormattedCounterValue(
                _pdh_freq_counter, win32pdh.PDH_FMT_DOUBLE
            )
            freq_current = round(freq_current, 1)
        else:
            freq_current = freq.current if freq else None

        cpu_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu_percent_total": psutil.cpu_percent(interval=None),
            "freq_current_mhz": freq_current,
            "freq_max_mhz": freq.max if freq else None,
        }
        return cpu_data


# -----------------------------
# Print CPU data when run directly
# -----------------------------
if __name__ == "__main__":
    import time
    CPUCollector.get_cpu_data()  # seed
    time.sleep(1)
    data = CPUCollector.get_cpu_data()
    print("=== Raw CPU Data ===")
    for key, value in data.items():
        print(f"{key}: {value}")
