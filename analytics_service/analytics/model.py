# analytics_service/analytics/model.py
# Author: Andrew Fox

# Loads the pre-trained Random Forest from model.pkl and exposes a predict() method.
# Takes a feature dict (from features.py), runs inference across all 12 labels,
# and returns component_risks and a list of detected issues ready for the GUI.
# Used by: AnalyticsThread in dashboard_service/gui/main.py

import pickle

from pathlib import Path
