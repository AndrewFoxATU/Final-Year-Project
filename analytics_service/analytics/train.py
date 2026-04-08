# analytics_service/analytics/train.py
# Author: Andrew Fox

# Loads training_data.csv, trains a multi-label Random Forest classifier,
# evaluates it with a train/test split, and saves the trained model to model.pkl.
# Run once by the developer before shipping the app.

# Usage: python -m analytics_service.analytics.train


import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
