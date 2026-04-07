# storage_service/schema.py
# Author: Andrew Fox
#
# Usage:
#   from storage_service.schema import init_db
#   conn = init_db("telemetry.db")

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union, Optional

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- ----------------------------
-- 1) Host + session metadata
-- ----------------------------

CREATE TABLE IF NOT EXISTS host (
  host_uuid          TEXT PRIMARY KEY,
  hostname           TEXT NOT NULL,
  mac_address        TEXT,
  os_name            TEXT,
  os_version         TEXT,
  machine            TEXT,
  cpu_model          TEXT,
  cpu_core_count     INTEGER,
  cpu_thread_count   INTEGER,
  total_ram_gb       REAL,
  gpu_detected       INTEGER NOT NULL DEFAULT 0,
  created_at_iso     TEXT NOT NULL,
  created_at_unix_ms INTEGER
);

-- One continuous run of the collector service
CREATE TABLE IF NOT EXISTS session (
  session_id         INTEGER PRIMARY KEY,
  host_uuid          TEXT NOT NULL REFERENCES host(host_uuid) ON DELETE CASCADE,
  started_at_iso     TEXT NOT NULL,
  started_at_unix_ms INTEGER NOT NULL,
  sample_interval_ms INTEGER
);

-- ----------------------------
-- 2) Sample index (one row per tick)
-- ----------------------------

CREATE TABLE IF NOT EXISTS sample (
  sample_id           INTEGER PRIMARY KEY,
  session_id          INTEGER NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
  ts_iso              TEXT NOT NULL,
  ts_unix_ms          INTEGER NOT NULL,
  collect_duration_ms INTEGER,
  dropped_metrics     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sample_session_ts ON sample(session_id, ts_unix_ms);

-- ------------------------------------
-- 3) RAM + swap
-- ------------------------------------

CREATE TABLE IF NOT EXISTS ram_sample (
  sample_id           INTEGER PRIMARY KEY REFERENCES sample(sample_id) ON DELETE CASCADE,
  used_ram_gb         REAL NOT NULL,
  ram_usage_percent   REAL NOT NULL,
  swap_usage_percent  REAL NOT NULL
);

-- ------------------------------------
-- 4) CPU
-- ------------------------------------

CREATE TABLE IF NOT EXISTS cpu_sample (
  sample_id                 INTEGER PRIMARY KEY REFERENCES sample(sample_id) ON DELETE CASCADE,
  cpu_percent_total         REAL NOT NULL,
  freq_current_mhz          REAL,
  freq_max_mhz              REAL
);


-- ------------------------------------
-- 5) GPU
-- ------------------------------------

CREATE TABLE IF NOT EXISTS gpu_device (
  gpu_uuid            TEXT PRIMARY KEY,
  host_uuid           TEXT NOT NULL REFERENCES host(host_uuid) ON DELETE CASCADE,
  gpu_name            TEXT,
  first_seen_iso      TEXT NOT NULL,
  first_seen_unix_ms  INTEGER
);

CREATE TABLE IF NOT EXISTS gpu_sample (
  sample_id            INTEGER NOT NULL REFERENCES sample(sample_id) ON DELETE CASCADE,
  gpu_uuid             TEXT NOT NULL REFERENCES gpu_device(gpu_uuid) ON DELETE CASCADE,
  gpu_id               INTEGER NOT NULL,

  gpu_util_percent     REAL NOT NULL,
  gpu_mem_util_percent REAL NOT NULL,
  gpu_mem_used_mb      INTEGER NOT NULL,

  gpu_temp_c           REAL NOT NULL,
  gpu_core_clock_mhz   REAL NOT NULL,

  gpu_power_usage_w    REAL NOT NULL,
  gpu_power_limit_w    REAL NOT NULL,

  PRIMARY KEY (sample_id, gpu_uuid)
);

CREATE INDEX IF NOT EXISTS idx_gpu_sample_sample ON gpu_sample(sample_id);

-- ------------------------------------
-- 6) Disk
-- ------------------------------------

CREATE TABLE IF NOT EXISTS disk_io_sample (
  sample_id            INTEGER PRIMARY KEY REFERENCES sample(sample_id) ON DELETE CASCADE,
  read_speed_bytes     REAL NOT NULL,
  write_speed_bytes    REAL NOT NULL,
  avg_read_latency_ms  REAL NOT NULL DEFAULT 0.0,
  avg_write_latency_ms REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS disk_partition (
  partition_id         INTEGER PRIMARY KEY,
  host_uuid            TEXT NOT NULL REFERENCES host(host_uuid) ON DELETE CASCADE,
  device               TEXT NOT NULL,
  mountpoint           TEXT NOT NULL,
  fstype               TEXT,
  first_seen_iso       TEXT NOT NULL,
  first_seen_unix_ms   INTEGER,
  UNIQUE(host_uuid, device, mountpoint)
);

CREATE TABLE IF NOT EXISTS disk_partition_sample (
  sample_id            INTEGER NOT NULL REFERENCES sample(sample_id) ON DELETE CASCADE,
  partition_id         INTEGER NOT NULL REFERENCES disk_partition(partition_id) ON DELETE CASCADE,

  total_gb             REAL NOT NULL,
  used_gb              REAL NOT NULL,
  usage_percent        REAL NOT NULL,

  PRIMARY KEY (sample_id, partition_id)
);

CREATE INDEX IF NOT EXISTS idx_disk_part_sample_part ON disk_partition_sample(partition_id);
"""


def connect(db_path: Union[str, Path]) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Pragmas: local telemetry logging
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA busy_timeout = 5000;")  # ms

    return conn


def init_db(
    db_path: Union[str, Path],
    *,
    conn: Optional[sqlite3.Connection] = None
) -> sqlite3.Connection:
    """
    Ensure schema exists. Returns a connection (existing or newly created).
    """
    if conn is None:
        conn = connect(db_path)

    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return conn
    except Exception:
        conn.rollback()
        raise
