# storage_service/storage/main.py
# Author: Andrew Fox

from __future__ import annotations

import datetime
from typing import Optional

from storage_service.storage.schema import init_db
from collector_service.collector.system_info_collector import SystemInfoCollector


class StorageManager:

    def __init__(self, db_path: str = "telemetry.db", sample_interval_ms: int = 1000):
        self.conn = init_db(db_path)

        now = datetime.datetime.now()
        ts_iso = now.isoformat()
        ts_unix_ms = int(now.timestamp() * 1000)

        info = SystemInfoCollector.get_system_info()

        # Register host (upsert by hostname)
        cur = self.conn.execute(
            "SELECT host_id FROM host WHERE hostname = ?", (info["hostname"],)
        )
        row = cur.fetchone()
        if row:
            self.host_id = row["host_id"]
        else:
            cur = self.conn.execute(
                """INSERT INTO host (hostname, os_name, os_version, machine, cpu_model, created_at_iso, created_at_unix_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (info["hostname"], info["os_name"], info["os_version"],
                 info["machine"], info["cpu_model"], ts_iso, ts_unix_ms),
            )
            self.conn.commit()
            self.host_id = cur.lastrowid

        # Register GPU devices
        self.gpu_uuid_map: dict[int, str] = {}
        for gpu in info["gpus"]:
            self.gpu_uuid_map[gpu["gpu_id"]] = gpu["gpu_uuid"]
            self.conn.execute(
                """INSERT OR IGNORE INTO gpu_device (gpu_uuid, host_id, gpu_name, gpu_id_first_seen, first_seen_iso, first_seen_unix_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (gpu["gpu_uuid"], self.host_id, gpu["gpu_name"], gpu["gpu_id"], ts_iso, ts_unix_ms),
            )
        self.conn.commit()

        # Open session
        cur = self.conn.execute(
            """INSERT INTO session (host_id, started_at_iso, started_at_unix_ms, sample_interval_ms)
               VALUES (?, ?, ?, ?)""",
            (self.host_id, ts_iso, ts_unix_ms, sample_interval_ms),
        )
        self.conn.commit()
        self.session_id = cur.lastrowid

        # Partition id cache: (device, mountpoint) -> partition_id
        # Pre-populate from DB so session restarts don't hit the INSERT OR IGNORE bug
        self.partition_id_map: dict[tuple, int] = {
            (row["device"], row["mountpoint"]): row["partition_id"]
            for row in self.conn.execute(
                "SELECT partition_id, device, mountpoint FROM disk_partition WHERE host_id = ?",
                (self.host_id,),
            ).fetchall()
        }

    # -----------------------------
    # Insert one tick of data
    # -----------------------------
    def insert_sample(self, cpu_data: dict, ram_data: dict,
                      gpu_data: Optional[dict], disk_data: dict,
                      collect_duration_ms: int = 0) -> None:
        now = datetime.datetime.now()
        ts_iso = now.isoformat()
        ts_unix_ms = int(now.timestamp() * 1000)

        dropped = 0
        if gpu_data is None:
            dropped += 1

        try:
            self.conn.execute("BEGIN")

            # -- sample row --
            cur = self.conn.execute(
                """INSERT INTO sample (session_id, ts_iso, ts_unix_ms, collect_duration_ms, dropped_metrics)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.session_id, ts_iso, ts_unix_ms, collect_duration_ms, 0),
            )
            sample_id = cur.lastrowid

            # -- CPU --
            try:
                self.conn.execute(
                    """INSERT INTO cpu_sample (sample_id, cpu_percent_total, freq_current_mhz, freq_max_mhz)
                       VALUES (?, ?, ?, ?)""",
                    (sample_id, cpu_data["cpu_percent_total"],
                     cpu_data.get("freq_current_mhz"), cpu_data.get("freq_max_mhz")),
                )
            except Exception:
                dropped += 1

            # -- RAM --
            try:
                self.conn.execute(
                    """INSERT INTO ram_sample
                         (sample_id, total_ram_gb, total_ram_round_gb, used_ram_gb,
                          ram_usage_percent, swap_usage_percent)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (sample_id, ram_data["total_ram_gb"], ram_data["total_ram_round_gb"],
                     ram_data["used_ram_gb"], ram_data["ram_usage_percent"],
                     ram_data["swap_usage_percent"]),
                )
            except Exception:
                dropped += 1

            # -- GPU --
            if gpu_data and gpu_data.get("gpus"):
                for gpu in gpu_data["gpus"]:
                    gpu_uuid = self.gpu_uuid_map.get(gpu["gpu_id"])
                    if not gpu_uuid:
                        continue
                    try:
                        self.conn.execute(
                            """INSERT INTO gpu_sample
                                 (sample_id, gpu_uuid, gpu_id,
                                  gpu_util_percent, gpu_mem_util_percent, gpu_mem_used_mb,
                                  gpu_temp_c, gpu_core_clock_mhz,
                                  gpu_power_usage_w, gpu_power_limit_w)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (sample_id, gpu_uuid, gpu["gpu_id"],
                             gpu["gpu_util_percent"], gpu["gpu_mem_util_percent"],
                             gpu["gpu_mem_used_mb"], gpu["gpu_temp_c"],
                             gpu["gpu_core_clock_mhz"], gpu["gpu_power_usage_w"],
                             gpu["gpu_power_limit_w"]),
                        )
                    except Exception:
                        dropped += 1

            # -- Disk IO --
            try:
                self.conn.execute(
                    """INSERT INTO disk_io_sample
                         (sample_id, read_speed_bytes, write_speed_bytes,
                          avg_read_latency_ms, avg_write_latency_ms)
                       VALUES (?, ?, ?, ?, ?)""",
                    (sample_id, disk_data["read_speed_bytes"], disk_data["write_speed_bytes"],
                     disk_data["avg_read_latency_ms"], disk_data["avg_write_latency_ms"]),
                )
            except Exception:
                dropped += 1

            # -- Disk partitions --
            for disk in disk_data.get("disks", []):
                key = (disk["device"], disk["mountpoint"])
                partition_id = self.partition_id_map.get(key)
                if partition_id is None:
                    cur = self.conn.execute(
                        """INSERT OR IGNORE INTO disk_partition
                             (host_id, device, mountpoint, fstype, first_seen_iso, first_seen_unix_ms)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (self.host_id, disk["device"], disk["mountpoint"],
                         disk.get("fstype"), ts_iso, ts_unix_ms),
                    )
                    if cur.lastrowid:
                        partition_id = cur.lastrowid
                    else:
                        row = self.conn.execute(
                            "SELECT partition_id FROM disk_partition WHERE host_id=? AND device=? AND mountpoint=?",
                            (self.host_id, disk["device"], disk["mountpoint"]),
                        ).fetchone()
                        partition_id = row["partition_id"]
                    self.partition_id_map[key] = partition_id

                try:
                    self.conn.execute(
                        """INSERT INTO disk_partition_sample
                             (sample_id, partition_id, total_gb, used_gb, usage_percent)
                           VALUES (?, ?, ?, ?, ?)""",
                        (sample_id, partition_id, disk["total_gb"],
                         disk["used_gb"], disk["usage_percent"]),
                    )
                except Exception:
                    dropped += 1

            # Update dropped count on the sample row
            if dropped:
                self.conn.execute(
                    "UPDATE sample SET dropped_metrics=? WHERE sample_id=?",
                    (dropped, sample_id),
                )

            self.conn.execute("COMMIT")

        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    # -----------------------------
    # Read
    # -----------------------------
    def get_recent_samples(self, n: int = 1000) -> list[dict]:
        rows = self.conn.execute(
            """SELECT
                 s.sample_id, s.ts_iso, s.ts_unix_ms,
                 c.cpu_percent_total, c.freq_current_mhz, c.freq_max_mhz,
                 r.total_ram_gb, r.total_ram_round_gb, r.used_ram_gb,
                 r.ram_usage_percent, r.swap_usage_percent,
                 g.gpu_util_percent, g.gpu_mem_util_percent, g.gpu_mem_used_mb,
                 g.gpu_temp_c, g.gpu_core_clock_mhz, g.gpu_power_usage_w, g.gpu_power_limit_w,
                 d.read_speed_bytes, d.write_speed_bytes,
                 d.avg_read_latency_ms, d.avg_write_latency_ms,
                 dp.usage_percent AS disk_usage_percent
               FROM sample s
               LEFT JOIN cpu_sample     c  ON c.sample_id  = s.sample_id
               LEFT JOIN ram_sample     r  ON r.sample_id  = s.sample_id
               LEFT JOIN gpu_sample     g  ON g.sample_id  = s.sample_id
               LEFT JOIN disk_io_sample d  ON d.sample_id  = s.sample_id
               LEFT JOIN disk_partition_sample dp ON dp.sample_id = s.sample_id
               WHERE s.session_id = ?
               ORDER BY s.ts_unix_ms DESC
               LIMIT ?""",
            (self.session_id, n),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_sample_count(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM sample WHERE session_id = ?",
            (self.session_id,),
        ).fetchone()
        return row["cnt"]

    def close(self) -> None:
        self.conn.close()
