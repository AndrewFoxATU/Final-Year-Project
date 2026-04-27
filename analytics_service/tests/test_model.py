# analytics_service/tests/test_model.py
# Author: Andrew Fox
# Run with: python -m pytest analytics_service/tests/test_model.py -v

from analytics_service.analytics.features import FeatureExtractor, WINDOW_SIZE
from analytics_service.analytics.labels import LABEL_NAMES, LABEL_COMPONENTS, LabelEngine
from analytics_service.analytics.model import PerformanceModel


# -----------------------------
# Shared helpers
# -----------------------------
def make_window(overrides_fn=None):
    """Build a WINDOW_SIZE list of samples (newest first)."""
    samples = []
    for i in range(WINDOW_SIZE):
        s = {
            "cpu_percent_total":    15.0,
            "freq_current_mhz":     2800.0,
            "ram_usage_percent":    50.0,
            "swap_usage_percent":   5.0,
            "gpu_util_percent":     5.0,
            "gpu_mem_util_percent": 20.0,
            "gpu_temp_c":           55.0,
            "gpu_core_clock_mhz":   300.0,
            "gpu_power_usage_w":    8.0,
            "gpu_power_limit_w":    150.0,
            "avg_read_latency_ms":  2.0,
            "avg_write_latency_ms": 2.0,
            "read_speed_bytes":     0.0,
            "write_speed_bytes":    0.0,
            "disk_usage_percent":   40.0,
        }
        if overrides_fn:
            s.update(overrides_fn(i))
        samples.append(s)
    return list(reversed(samples))


MODEL = PerformanceModel()


# -----------------------------
# Model loading
# -----------------------------
class TestModelLoads:

    def test_model_has_feature_cols(self):
        assert len(MODEL._feature_cols) > 0

    def test_model_has_correct_label_names(self):
        assert MODEL._label_names == LABEL_NAMES

    def test_model_object_exists(self):
        assert MODEL._model is not None


# -----------------------------
# Predict output structure
# -----------------------------
class TestPredictOutputStructure:

    def test_predict_returns_dict(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        assert isinstance(result, dict)

    def test_predict_has_issues_key(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        assert "issues" in result

    def test_predict_has_component_risks_key(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        assert "component_risks" in result

    def test_issues_is_list(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        assert isinstance(result["issues"], list)

    def test_component_risks_has_all_components(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        for component in set(LABEL_COMPONENTS.values()):
            assert component in result["component_risks"]

    def test_component_risk_values_are_0_1_or_2(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        for val in result["component_risks"].values():
            assert val in (0, 1, 2)

    def test_issues_only_contains_valid_labels(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        for issue in result["issues"]:
            assert issue in LABEL_NAMES


# -----------------------------
# Healthy baseline
# -----------------------------
class TestHealthyPrediction:

    def test_healthy_window_no_issues(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        assert result["issues"] == []

    def test_healthy_window_all_risks_zero(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        for val in result["component_risks"].values():
            assert val == 0


# -----------------------------
# Issue detection
# -----------------------------
class TestIssueDetection:

    def test_detects_cpu_sustained_high_load(self):
        def fn(i):
            return {"cpu_percent_total": 88.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "cpu_sustained_high_load" in result["issues"]

    def test_detects_cpu_bottleneck(self):
        def fn(i):
            return {"cpu_percent_total": 95.0, "ram_usage_percent": 45.0, "disk_usage_percent": 30.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "cpu_bottleneck" in result["issues"]

    def test_detects_cpu_thermal_throttle(self):
        def fn(i):
            return {"cpu_percent_total": 85.0, "freq_current_mhz": 3200.0 - i * 180}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "cpu_thermal_throttle" in result["issues"]

    def test_detects_ram_pressure(self):
        def fn(i):
            return {"ram_usage_percent": 87.0, "cpu_percent_total": 20.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "ram_pressure" in result["issues"]

    def test_detects_excessive_swap(self):
        def fn(i):
            return {"swap_usage_percent": 60.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "excessive_swap_usage" in result["issues"]

    def test_detects_disk_full(self):
        def fn(i):
            return {"disk_usage_percent": 93.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "disk_full" in result["issues"]

    def test_detects_disk_high_latency(self):
        def fn(i):
            return {"avg_read_latency_ms": 35.0, "avg_write_latency_ms": 30.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "disk_high_latency" in result["issues"]

    def test_detects_gpu_overheating(self):
        def fn(i):
            return {"gpu_temp_c": 90.0, "gpu_util_percent": 95.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert "gpu_overheating" in result["issues"]

    def test_detects_gpu_vram_pressure(self):
        def fn(i):
            return {"gpu_mem_util_percent": 93.0}
        features = FeatureExtractor.compute(make_window(fn))
        assert LabelEngine.apply(features)["gpu_vram_pressure"]


# -----------------------------
# Component risk levels
# -----------------------------
class TestComponentRisks:

    def test_cpu_risk_1_for_one_issue(self):
        def fn(i):
            return {"cpu_percent_total": 88.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert result["component_risks"]["CPU"] >= 1

    def test_gpu_risk_0_on_healthy(self):
        features = FeatureExtractor.compute(make_window())
        result = MODEL.predict(features)
        assert result["component_risks"]["GPU"] == 0

    def test_disk_risk_1_when_full(self):
        def fn(i):
            return {"disk_usage_percent": 93.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert result["component_risks"]["Disk"] >= 1

    def test_ram_risk_1_when_pressured(self):
        def fn(i):
            return {"ram_usage_percent": 87.0, "cpu_percent_total": 20.0}
        features = FeatureExtractor.compute(make_window(fn))
        result = MODEL.predict(features)
        assert result["component_risks"]["RAM"] >= 1

    def test_missing_feature_does_not_crash(self):
        features = FeatureExtractor.compute(make_window())
        features.pop(list(features.keys())[0])
        result = MODEL.predict(features)
        assert "issues" in result
