# collector_service/collector/disk_collector.py
# Author: Andrew Fox

import psutil
import datetime

class DiskCollector:
    """
    Collects disk usage, capacity, read/write speed, and usage percentage.
    Suitable for monitoring and future ML analysis.
    """

    last_disk_io = psutil.disk_io_counters()
    last_timestamp = datetime.datetime.now()

    @staticmethod
    def get_disk_data():
        now = datetime.datetime.now()
        current_io = psutil.disk_io_counters()
        time_diff = (now - DiskCollector.last_timestamp).total_seconds()

        read_speed = 0
        write_speed = 0

        read_count_delta  = 0
        write_count_delta = 0
        avg_read_latency_ms  = 0.0
        avg_write_latency_ms = 0.0

        if time_diff > 0:
            read_speed        = (current_io.read_bytes  - DiskCollector.last_disk_io.read_bytes)  / time_diff
            write_speed       = (current_io.write_bytes - DiskCollector.last_disk_io.write_bytes) / time_diff

            read_count_delta  = current_io.read_count  - DiskCollector.last_disk_io.read_count
            write_count_delta = current_io.write_count - DiskCollector.last_disk_io.write_count
            read_time_delta   = current_io.read_time   - DiskCollector.last_disk_io.read_time
            write_time_delta  = current_io.write_time  - DiskCollector.last_disk_io.write_time

            if read_count_delta  > 0:
                avg_read_latency_ms  = read_time_delta  / read_count_delta
            if write_count_delta > 0:
                avg_write_latency_ms = write_time_delta / write_count_delta

        DiskCollector.last_disk_io = current_io
        DiskCollector.last_timestamp = now

        partitions = psutil.disk_partitions()
        disk_list = []

        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                continue

            used_gb = round(usage.used / (1024**3), 2)
            total_gb = round(usage.total / (1024**3), 2)
            percent = usage.percent

            disk_list.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "usage_percent": percent,
            })

        return {
            "timestamp": now.isoformat(),
            "read_speed_bytes": read_speed,
            "write_speed_bytes": write_speed,
            "avg_read_latency_ms": avg_read_latency_ms,
            "avg_write_latency_ms": avg_write_latency_ms,
            "disks": disk_list,
        }


# -----------------------------
# Print Disk data when run directly
# -----------------------------
if __name__ == "__main__":
    data = DiskCollector.get_disk_data()
    print("=== Disk Data ===")
    for key, value in data.items():
        print(f"{key}: {value}")
