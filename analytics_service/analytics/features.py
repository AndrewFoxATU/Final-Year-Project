# analytics_service/analytics/features.py
# Author: Andrew Fox

# Converts a window of raw telemetry samples (from StorageManager.get_recent_samples)
# into a single flat feature vector ready for ML inference or training.
# Computes rolling statistics (mean, std, slope) over the window for key metrics.
# Used by: generate_training_data.py, collect_real_data.py, model.py

import numpy as np
from typing import Optional
