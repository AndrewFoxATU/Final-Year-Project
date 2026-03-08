<div align="center">

# Smart System Performance Dashboard

**Real-time hardware monitoring with ML-powered diagnostics**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-Only-0078D6?style=for-the-badge&logo=windows&logoColor=white)

*Final Year Project — Andrew Fox, ATU*

</div>

---

## Overview

A desktop application that collects live hardware telemetry (CPU, RAM, GPU, Disk), stores it persistently in a local SQLite database, and uses a pre-trained Random Forest classifier to detect hardware performance issues in real time — from the moment the app launches.

---

## Features

| | Feature | Description |
|---|---|---|
| 📊 | **Live Monitoring** | Real-time graphs for CPU, RAM, GPU, and Disk with hover labels |
| 💾 | **Persistent Telemetry** | Every metric stored to SQLite every second via a non-blocking background thread |
| 🤖 | **ML Diagnostics** | Pre-trained Random Forest detects 12 hardware issue types instantly on launch |
| 🎨 | **Dark Theme UI** | Custom QSS dark theme with configurable accent colour |
| ⚙️ | **Settings** | Graph refresh rate and accent colour, persisted across sessions |

---

## Requirements

- **Windows only** — uses `winreg` and `pywin32` for system information
- **Python 3.11+**
- **NVIDIA GPU optional** — GPU monitoring uses NVML; the app runs fine without one

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
│
├── collector_service/
│   └── collector/
│       ├── cpu_collector.py          # CPU usage and frequency
│       ├── ram_collector.py          # RAM and swap usage
│       ├── gpu_collector.py          # NVIDIA GPU metrics via NVML
│       ├── disk_collector.py         # Disk IO speeds, latency, partition usage
│       └── system_info_collector.py  # One-time startup: hostname, OS, CPU/GPU model
│
├── storage_service/
│   └── storage/
│       ├── schema.py                 # SQLite schema and init_db()
│       └── main.py                   # StorageManager — persists all telemetry
│
├── analytics_service/
│   └── analytics/
│       ├── features.py               # Feature matrix builder with rolling stats
│       ├── labels.py                 # Rule-based labeller for 12 issue types
│       └── model.py                  # Random Forest wrapper (MultiOutputClassifier)
│
├── dashboard_service/
│   ├── assets/
│   │   ├── fonts/                    # Inter font
│   │   └── styles/style.qss          # Global dark theme QSS
│   └── gui/
│       ├── main.py                   # Main window, StorageThread, app entry point
│       ├── live_monitor.py           # Live graphs and metric labels
│       ├── analytics_view.py         # Analytics tab UI
│       └── settings_manager.py       # Load/save settings JSON
│
├── telemetry.db                      # SQLite database (auto-created on first run)
└── requirements.txt
```

---

## Architecture

```
App Start
  │
  ├── StorageThread  (QThread — background)
  │     └── Every 1 second:
  │           ├── CPUCollector.get_cpu_data()
  │           ├── RAMCollector.get_ram_data()
  │           ├── GPUCollector.get_gpu_data()    ← gracefully skipped if no NVIDIA GPU
  │           ├── DiskCollector.get_disk_data()
  │           └── StorageManager.insert_sample() ──► telemetry.db
  │
  └── UI  (main thread — never blocked by storage)
        ├── LiveSystemMonitor  ──► real-time graphs  (own QTimer)
        └── AnalyticsWidget    ──► reads DB every 5s, runs model, shows risk scores
```

---

## ML Approach

The analytics module ships with a **pre-trained Random Forest** (`MultiOutputClassifier` wrapping `RandomForestClassifier`), trained offline by the developer on a controlled synthetic dataset. Predictions are available from the very first launch — no warm-up period required.

### Training Pipeline

```
Synthetic Dataset  ──►  Rule-Based Label Engine  ──►  RandomForestClassifier  ──►  model.pkl
 (developer-built)        (12 issue labels)             (100 trees, balanced)      (bundled)
```

1. Developer generates synthetic feature vectors covering healthy and all issue states
2. Rule engine programmatically labels each sample (weak supervision)
3. Model trained with `class_weight='balanced'` and saved as `model.pkl`
4. `model.pkl` bundled and loaded at app startup

### Prediction Pipeline *(every 5 seconds)*

```
telemetry.db  ──►  Feature Matrix  ──►  100 Trees Vote  ──►  Component Risk Scores  ──►  UI
                   (+ rolling stats)     (probability)         CPU / RAM / GPU / Disk
```

**Personalisation (optional):** Accumulated live telemetry can periodically retrain the model in the background to improve accuracy for the specific machine.

### Detected Issue Types

| Component | Issues Detected |
|:---:|---|
| **CPU** | Thermal throttling · Bottleneck · Sustained high load |
| **RAM** | Memory pressure · Memory leak · Excessive swap |
| **Disk** | Disk full · IO bottleneck · High latency |
| **GPU** | Overheating · Power throttling · VRAM pressure |

---

<div align="center">
<sub>Built with PyQt6 · scikit-learn · psutil · SQLite</sub>
</div>
