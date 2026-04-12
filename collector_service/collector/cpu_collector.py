# collector_service/collector/cpu_collector.py
# Author: Andrew Fox

import win32pdh
import psutil
import datetime

# '\Processor Information(_Total)\Actual Frequency' exists on Windows 11 and
# returns the true real-time frequency including turbo boost.
# On Windows 10 that counter may not exist at all, so we fall back to
# '\Processor Information(_Total)\% Processor Performance':
#   actual_mhz = (perf_pct / 100) * base_mhz
# Each counter is added in its own try block so one missing counter
# does not prevent the other from being set up.

_base_freq_mhz = None
try:
    _f = psutil.cpu_freq(percpu=False)
    if _f:
        _base_freq_mhz = _f.current  # base/nominal clock in MHz (e.g. 3600.0)
except Exception:
    pass

_pdh_query = None
_pdh_freq_counter = None   # Actual Frequency  (Windows 11)
_pdh_perf_counter = None   # % Processor Performance  (Windows 10 fallback)

try:
    _pdh_query = win32pdh.OpenQuery()
except Exception:
    _pdh_query = None

if _pdh_query is not None:
    try:
        _pdh_freq_counter = win32pdh.AddCounter(
            _pdh_query,
            r"\Processor Information(_Total)\Actual Frequency"
        )
    except Exception:
        _pdh_freq_counter = None

    try:
        _pdh_perf_counter = win32pdh.AddCounter(
            _pdh_query,
            r"\Processor Information(_Total)\% Processor Performance"
        )
    except Exception:
        _pdh_perf_counter = None

    try:
        win32pdh.CollectQueryData(_pdh_query)  # seed — real value available next call
    except Exception:
        _pdh_query = None


class CPUCollector:
    # Collects raw CPU data suitable for logging and ML analysis.

    @staticmethod
    def get_cpu_data():
        freq_current = None

        if _pdh_query is not None:
            try:
                win32pdh.CollectQueryData(_pdh_query)

                if _pdh_freq_counter is not None:
                    _, val = win32pdh.GetFormattedCounterValue(
                        _pdh_freq_counter, win32pdh.PDH_FMT_DOUBLE
                    )
                    freq_current = round(val, 1)
                elif _pdh_perf_counter is not None and _base_freq_mhz:
                    _, perf_pct = win32pdh.GetFormattedCounterValue(
                        _pdh_perf_counter, win32pdh.PDH_FMT_DOUBLE
                    )
                    freq_current = round((perf_pct / 100.0) * _base_freq_mhz, 1)
            except Exception:
                freq_current = None

        if freq_current is None:
            freq = psutil.cpu_freq(percpu=False)
            freq_current = freq.current if freq else None

        cpu_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu_percent_total": psutil.cpu_percent(interval=None),
            "freq_current_mhz": freq_current,
        }
        return cpu_data


# -----------------------------
# Print CPU data when run directly
# -----------------------------
if __name__ == "__main__":
    import time
    print(f"Actual Frequency counter : {'available' if _pdh_freq_counter else 'NOT FOUND'}")
    print(f"% Processor Perf counter : {'available' if _pdh_perf_counter else 'NOT FOUND'}")
    print(f"Base freq (psutil)       : {_base_freq_mhz} MHz")
    print()
    CPUCollector.get_cpu_data()  # seed
    time.sleep(1)
    data = CPUCollector.get_cpu_data()
    print("=== Raw CPU Data ===")
    for key, value in data.items():
        print(f"{key}: {value}")