# analytics_service/analytics/labels.py
# Author: Andrew Fox

# Applies 12 rule-based boolean labels to a feature dict produced by features.py.
# Rules encode domain knowledge thresholds for each issue type (e.g. cpu_thermal_throttle,
# ram_pressure, disk_full). Used to label synthetic and real training data.
# Used by: generate_training_data.py, collect_real_data.py

