# storage_service/tests/test_storage.py
# Author: Andrew Fox
# Run with: python -m pytest storage_service/tests/test_storage.py -v

import pytest
from storage_service.storage.main import StorageManager


# -----------------------------
# Shared sample data
# -----------------------------
CPU_DATA = {
    "timestamp": "2026-01-01T00:00:00",
    "cpu_percent_total": 25.0,
    "freq_current_mhz": 2800.0,
}

RAM_DATA = {
    "timestamp": "2026-01-01T00:00:00",
    "total_ram_gb": 16.0,
    "total_ram_round_gb": 16,
    "used_ram_gb": 8.0,
    "ram_usage_percent": 50.0,
    "swap_usage_percent": 5.0,
}

DISK_DATA = {
    "read_speed_bytes": 0.0,
    "write_speed_bytes": 0.0,
    "avg_read_latency_ms": 1.0,
    "avg_write_latency_ms": 1.0,
    "disks": [
        {
            "device": "C:\\",
            "mountpoint": "C:\\",
            "fstype": "NTFS",
            "total_gb": 500.0,
            "used_gb": 200.0,
            "usage_percent": 40.0,
        }
    ],
}


@pytest.fixture
def storage():
    """Fresh in-memory StorageManager for each test."""
    s = StorageManager(db_path=":memory:")
    yield s
    s.close()


# -----------------------------
# Host Registration
# -----------------------------
class TestHostRegistration:

    def test_host_uuid_is_set(self, storage):
        assert storage.host_uuid is not None
        assert len(storage.host_uuid) > 0

    def test_host_uuid_is_string(self, storage):
        assert isinstance(storage.host_uuid, str)

    def test_host_registered_in_db(self, storage):
        row = storage.conn.execute(
            "SELECT * FROM host WHERE host_uuid = ?", (storage.host_uuid,)
        ).fetchone()
        assert row is not None

    def test_host_has_cpu_max_mhz(self, storage):
        result = storage.get_host_cpu_max_mhz()
        assert result is None or result > 0

    def test_host_mac_address_stored(self, storage):
        row = storage.conn.execute(
            "SELECT mac_address FROM host WHERE host_uuid = ?", (storage.host_uuid,)
        ).fetchone()
        assert row["mac_address"] is not None


# -----------------------------
# Session
# -----------------------------
class TestSession:

    def test_session_id_is_set(self, storage):
        assert storage.session_id is not None
        assert storage.session_id > 0

    def test_session_registered_in_db(self, storage):
        row = storage.conn.execute(
            "SELECT * FROM session WHERE session_id = ?", (storage.session_id,)
        ).fetchone()
        assert row is not None

    def test_session_linked_to_host(self, storage):
        row = storage.conn.execute(
            "SELECT host_uuid FROM session WHERE session_id = ?", (storage.session_id,)
        ).fetchone()
        assert row["host_uuid"] == storage.host_uuid


# -----------------------------
# Insert Sample
# -----------------------------
class TestInsertSample:

    def test_insert_sample_no_error(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)

    def test_sample_count_increments(self, storage):
        assert storage.get_sample_count() == 0
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        assert storage.get_sample_count() == 1
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        assert storage.get_sample_count() == 2

    def test_insert_multiple_samples(self, storage):
        for _ in range(5):
            storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        assert storage.get_sample_count() == 5


# -----------------------------
# Read Samples
# -----------------------------
class TestReadSamples:

    def test_get_recent_samples_empty(self, storage):
        assert storage.get_recent_samples() == []

    def test_get_recent_samples_returns_inserted(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        samples = storage.get_recent_samples()
        assert len(samples) == 1

    def test_get_recent_samples_respects_limit(self, storage):
        for _ in range(10):
            storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        samples = storage.get_recent_samples(n=5)
        assert len(samples) == 5

    def test_get_recent_samples_returns_dicts(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        samples = storage.get_recent_samples()
        assert isinstance(samples[0], dict)

    def test_get_recent_samples_all_sessions_returns_inserted(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        samples = storage.get_recent_samples_all_sessions()
        assert len(samples) == 1

    def test_sample_contains_cpu_data(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        sample = storage.get_recent_samples()[0]
        assert sample["cpu_percent_total"] == pytest.approx(25.0)

    def test_sample_contains_ram_data(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        sample = storage.get_recent_samples()[0]
        assert sample["ram_usage_percent"] == pytest.approx(50.0)

    def test_sample_contains_disk_data(self, storage):
        storage.insert_sample(CPU_DATA, RAM_DATA, None, DISK_DATA)
        sample = storage.get_recent_samples()[0]
        assert sample["disk_usage_percent"] == pytest.approx(40.0)
