# collector_service/collector/disk_collector.py
# Author: Andrew Fox

import psutil
import datetime
import math

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

        if time_diff > 0:
            read_speed = (current_io.read_bytes - DiskCollector.last_disk_io.read_bytes) / time_diff
            write_speed = (current_io.write_bytes - DiskCollector.last_disk_io.write_bytes) / time_diff

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
                "total_gb": total_gb,
                "used_gb": used_gb,
                "usage_percent": percent,
            })

        return {
            "timestamp": now.isoformat(),
            "read_speed_bytes": read_speed,
            "write_speed_bytes": write_speed,
            "disks": disk_list,
        }


if __name__ == "__main__":
    print(DiskCollector.get_disk_data())
