# analytics_service/analytics/collect_real_data.py
# Author: Andrew Fox

# Reads a real telemetry.db file, computes features and labels for each sample window,
# and appends the rows to training_data.csv alongside synthetic data.
# Supports an optional --anonymise flag to strip host identity before processing.

# Usage: python -m analytics_service.analytics.collect_real_data --db path/to/telemetry.db

import argparse
import csv
from pathlib import Path

from storage_service.storage.schema import init_db
