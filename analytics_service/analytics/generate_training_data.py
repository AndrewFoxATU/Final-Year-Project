# analytics_service/analytics/generate_training_data.py
# Author: Andrew Fox

# Generates a synthetic labelled training dataset covering all 12 issue types.
# Each scenario constructs a window of realistic raw metric samples with controlled
# values and noise, computes features via features.py, applies labels via labels.py,
# and appends the result to training_data.csv.
# Run directly by the developer before shipping the model.

# Usage: python -m analytics_service.analytics.generate_training_data

import csv
import random
import numpy as np
from pathlib import Path

from analytics_service.analytics.features import compute_features
from analytics_service.analytics.labels import apply_labels
