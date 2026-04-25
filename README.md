<div align="center">

# Smart System Performance Dashboard
**Real-time hardware monitoring with ML-powered diagnostics**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-Only-0078D6?style=for-the-badge&logo=windows&logoColor=white)

*Final Year Project -- Andrew Fox, ATU*

</div>

---

## Overview

A desktop application that collects live hardware telemetry (CPU, RAM, GPU, Disk), stores it persistently in a local SQLite database, and uses a pre-trained Random Forest classifier to detect hardware performance issues in real time. All processing runs entirely on the user's machine with no cloud dependency.

---

## Features

| Feature | Description |
|---|---|
| **Live Monitoring** | Real-time graphs for CPU, RAM, GPU, and Disk with hover labels |
| **Persistent Telemetry** | Every metric stored to SQLite every second via a background thread |
| **ML Diagnostics** | Pre-trained Random Forest detects 12 hardware issue types, with plain-language descriptions and fix suggestions |
| **Health Score** | Continuous 0-100 score derived from a severity-weighted, confidence-scaled penalty formula across all active fault labels |
| **Alerts Log** | Persistent log of all detected issues across the session, viewable via the Alerts button |
| **Export DB** | Full telemetry database exportable to CSV with host info, session metadata, and per-second sample data |
| **Settings** | Graph refresh rate and accent colour, persisted across sessions |

---

## Requirements

- **Windows only** -- uses `pywin32` for accurate CPU frequency via Windows PDH counters
- **Python 3.11+**
- **NVIDIA GPU optional** -- GPU monitoring uses NVML; the app runs fine without one

---

## Setup

```bash
git clone https://github.com/AndrewFoxATU/Final-Year-Project.git
cd Final-Year-Project
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/Scripts/activate     # Git Bash / VS Code terminal
venv\Scripts\activate.bat        # CMD
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Running

```bash
python -m dashboard_service.gui.main
```

> Must be launched as a module from the project root for package imports to resolve correctly.

---

## Project Structure

```
final-year-project/
|
|-- collector_service/
|   |-- collector/
|   |   |-- cpu_collector.py          # CPU usage and frequency (psutil + pywin32 PDH)
|   |   |-- ram_collector.py          # RAM and swap usage
|   |   |-- gpu_collector.py          # NVIDIA GPU metrics via pynvml
|   |   |-- disk_collector.py         # Disk I/O speeds, latency, partition usage
|   |   └── system_info_collector.py  # One-time startup: hostname, OS, CPU/GPU model
|   └── tests/
|       └── test_collectors.py
|
|-- storage_service/
|   |-- storage/
|   |   |-- schema.py                 # SQLite schema (10 tables) and init_db()
|   |   └── main.py                   # StorageManager -- persists all telemetry, WAL mode
|   └── tests/
|       └── test_storage.py
|
|-- analytics_service/
|   |-- analytics/
|   |   |-- features.py               # 35-feature vector builder with rolling statistics
|   |   |-- labels.py                 # Rule-based labeller for 12 fault types and severity ratings
|   |   |-- model.py                  # Random Forest wrapper -- inference and health score
|   |   |-- train.py                  # Offline training script -- produces model.pkl
|   |   |-- generate_training_data.py # Synthetic dataset generator (12 scenario builders)
|   |   └── collect_real_data.py      # Appends real telemetry from .db files to training CSV
|   |-- tests/
|   |   |-- test_labels.py
|   |   └── test_model.py
|   └── visualisations/               # 10 post-training analysis scripts (not used at runtime)
|
|-- dashboard_service/
|   |-- assets/
|   |   |-- fonts/                    # Inter font
|   |   └── styles/style.qss          # Global QSS stylesheet with accent colour token
|   └── gui/
|       |-- main.py                   # Main window, StorageThread, app entry point
|       |-- live_monitor.py           # Live graphs and metric labels
|       |-- analytics_view.py         # Analytics tab -- AnalyticsThread, issue cards, health score
|       └── settings_manager.py       # Load/save settings JSON
|
|-- analytics_service/data/
|   |-- model.pkl                     # Trained model (loaded at startup, not retrained at runtime)
|   └── training_data.csv             # 20,872-row labelled dataset (synthetic + real)
|
|-- telemetry.db                      # SQLite database (auto-created on first run)
└── requirements.txt
```

---

## Architecture

```
App Start
  |
  |-- StorageThread  (QThread -- background)
  |     └── Every 1 second:
  |           |-- CPUCollector.get_cpu_data()
  |           |-- RAMCollector.get_ram_data()
  |           |-- GPUCollector.get_gpu_data()    <- gracefully skipped if no NVIDIA GPU
  |           |-- DiskCollector.get_disk_data()
  |           └── StorageManager.insert_sample() --> telemetry.db
  |
  |-- AnalyticsThread  (QThread -- background)
  |     └── Waits for 200 samples, then every 5 seconds:
  |           |-- Reads last 10 samples from telemetry.db
  |           |-- FeatureExtractor.compute()  --> 35-feature vector
  |           |-- PerformanceModel.predict()  --> issues + health score
  |           └── Emits results to AnalyticsWidget (UI thread)
  |
  └── UI  (main thread -- never blocked)
        |-- LiveSystemMonitor  --> real-time graphs  (configurable QTimer)
        └── AnalyticsWidget    --> health score, issue cards, alerts log
```

---

## ML Approach

The analytics module ships with a pre-trained Random Forest (`MultiOutputClassifier` wrapping `RandomForestClassifier`), trained offline on a labelled dataset of 20,872 samples. Once 200 samples have been collected the application begins running inference every 5 seconds with no further setup required.

### Training Pipeline

```
Synthetic Scenarios  -->  Rule-Based Label Engine  -->  RandomForestClassifier  -->  model.pkl
Real Telemetry (x3)       (12 fault labels, 1-5         (200 trees, balanced,       (bundled)
                           severity ratings)              MultiOutputClassifier)
```

1. `generate_training_data.py` builds 12 scenario builders, one per fault type, each generating 500-800 synthetic windows with +/-12% metric jitter
2. `collect_real_data.py` appends real telemetry collected from 3 physical machines (Windows 10 and Windows 11, with and without a discrete GPU)
3. The rule-based `LabelEngine` labels every window across both sources (weak supervision)
4. Model trained with `class_weight='balanced'` and serialised to `model.pkl` alongside the feature column names and label names
5. Total training set: 20,872 rows -- average F1 score of 0.98 across all 12 labels

### Prediction Pipeline (every 5 seconds, after 200-sample warmup)

```
telemetry.db  -->  10-sample window  -->  35 features  -->  12-label prediction  -->  UI
                   (last 10 seconds)      (point-in-time     (binary + confidence     health score
                                          + rolling stats)    probabilities)           issue cards
```

### Detected Issue Types

| Component | Issues Detected |
|:---:|---|
| **CPU** | Thermal throttling, Bottleneck, Sustained high load |
| **RAM** | Memory pressure, Memory leak, Excessive swap |
| **Disk** | Disk full, I/O bottleneck, High latency |
| **GPU** | Overheating, Power throttling, VRAM pressure |

Each detected issue includes a plain-language description of the problem and a suggested fix, displayed directly in the Analytics panel.

---

<div align="center">
<sub>Built with PyQt6 · scikit-learn · psutil · pynvml · SQLite</sub>
</div>
