# dashboard_service/gui/main.py
# Author: Andrew Fox
# Run with: python -m dashboard_service.gui.main
# -----------------------------
# Imports
# -----------------------------
import csv
import sqlite3
import sys
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGridLayout, QSizePolicy, QDialog,
    QComboBox, QSpinBox, QColorDialog, QLineEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QFontDatabase, QFont, QCursor, QColor
import pyqtgraph as pg

# Import collectors
from collector_service.collector.cpu_collector import CPUCollector
from collector_service.collector.ram_collector import RAMCollector
from collector_service.collector.gpu_collector import GPUCollector
from collector_service.collector.disk_collector import DiskCollector
from storage_service.storage.main import StorageManager

# Import the Live System Monitoring panel
from dashboard_service.gui.live_monitor import LiveSystemMonitor
# Import the Analytics panel
from dashboard_service.gui.analytics_view import AnalyticsWidget, AlertsDialog
# Import settings manager
from dashboard_service.gui.settings_manager import load_settings, save_settings


# -----------------------------
# Background Storage Thread
# -----------------------------
class StorageThread(QThread):
    """Collects and stores one sample per second in a background thread."""

    def run(self):
        storage = StorageManager(db_path="telemetry.db", sample_interval_ms=1000)
        try:
            while not self.isInterruptionRequested():
                try:
                    _t0 = time.perf_counter()
                    cpu = CPUCollector.get_cpu_data()
                    ram = RAMCollector.get_ram_data()
                    try:
                        gpu = GPUCollector.get_gpu_data()
                    except Exception:
                        gpu = None
                    disk = DiskCollector.get_disk_data()
                    collect_ms = int((time.perf_counter() - _t0) * 1000)
                    storage.insert_sample(cpu, ram, gpu, disk, collect_ms)
                except Exception:
                    pass
                self.msleep(1000)
        finally:
            storage.close()


# -----------------------------
# Main Dashboard Window
# -----------------------------
class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart System Performance Dashboard")
        self.setGeometry(100, 100, 1200, 700)

        # Load settings
        self.settings_data = load_settings()

        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.central_widget.setLayout(self.main_layout)

        # Top bar
        self.top_bar()

        # Content area
        self.content_area()

        # Initialize content widgets
        self.arrange_sections()

        # Bottom navigation bar
        self.bottom_bar()

        # Default Mode: Live Monitoring
        self.set_active_button(self.live_button)
        self.content_widgets["Live System Monitoring"].show()

        # Start background storage thread
        self._storage_thread = StorageThread(self)
        self._storage_thread.start()

    def closeEvent(self, event):
        self.analytics_widget.shutdown()
        self._storage_thread.requestInterruption()
        self._storage_thread.wait()
        super().closeEvent(event)

    # -----------------------------
    # Top Bar
    # -----------------------------
    def top_bar(self):
        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBar")
        self.top_bar.setFixedHeight(90)
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(20, 0, 20, 0)
        self.top_bar.setLayout(self.top_layout)
        self.main_layout.addWidget(self.top_bar)

        title_block = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 14, 0, 14)
        title_layout.setSpacing(2)
        title_block.setLayout(title_layout)

        label_line = QLabel("Final Year Project  ·  Python  ·  Machine Learning  ·  Desktop Application")
        label_line.setObjectName("topBarLabel")
        title = QLabel("Smart System Performance Dashboard")
        title.setObjectName("topBarTitle")
        subtitle = QLabel("Real-time hardware monitoring and ML-based fault detection")
        subtitle.setObjectName("topBarSub")
        title_layout.addWidget(label_line)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        self.top_layout.addWidget(title_block, stretch=1)

        # Alerts, Export DB & Settings buttons
        self.alerts_button = QPushButton("Alerts")
        self.alerts_button.clicked.connect(self.open_alerts_dialog)
        self.export_db_button = QPushButton("Export DB")
        self.export_db_button.clicked.connect(self.export_db_to_csv)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)

        for button in [self.alerts_button, self.settings_button]:
            button.setObjectName("topButton")
            button.setFixedSize(80, 36)

        self.export_db_button.setObjectName("topButton")
        self.export_db_button.setFixedSize(105, 36)

        for button in [self.alerts_button, self.export_db_button, self.settings_button]:
            self.top_layout.addWidget(button)

    # -----------------------------
    # Content Area
    # -----------------------------
    def content_area(self):
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_frame.setLayout(self.content_layout)
        self.main_layout.addWidget(self.content_frame, stretch=1)

    # -----------------------------
    # Arrange Sections (Panels)
    # -----------------------------
    def arrange_sections(self):
        # Import and use LiveSystemMonitor as a self-contained widget
        self.live_monitor_widget = LiveSystemMonitor(self)

        self.analytics_widget = AnalyticsWidget(self)

        # Create main content mapping
        self.content_widgets = {
            "Live System Monitoring": self.live_monitor_widget,
            "Analytics": self.analytics_widget,
        }

        # Add each widget to the content layout
        for widget in self.content_widgets.values():
            if isinstance(widget, QLabel):
                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(widget)
            widget.hide()

    # -----------------------------
    # Bottom Navigation Bar
    # -----------------------------
    def bottom_bar(self):
        self.bottom_bar = QFrame()
        self.bottom_bar.setObjectName("bottomBar")
        self.bottom_layout = QHBoxLayout()
        self.bottom_bar.setLayout(self.bottom_layout)
        self.main_layout.addWidget(self.bottom_bar)

        # Navigation buttons
        self.live_button = QPushButton("Live System Monitoring")
        self.analytics_button = QPushButton("Analytics")

        self.bottom_buttons = [
            self.live_button,
            self.analytics_button,
        ]

        for button in self.bottom_buttons:
            button.setObjectName("bottomButton")
            button.setMinimumHeight(50)
            self.bottom_layout.addWidget(button)
            button.clicked.connect(lambda _, b=button: self.switch_mode(b.text()))

    # -----------------------------
    # Mode Switching
    # -----------------------------
    def switch_mode(self, mode_name):
        # Hide all widgets, show the selected one
        for widget in self.content_widgets.values():
            widget.hide()
        self.content_widgets[mode_name].show()

        mapping = {
            "Live System Monitoring": self.live_button,
            "Analytics": self.analytics_button,
        }
        self.set_active_button(mapping[mode_name])

    # -----------------------------
    # Active Button Styling
    # -----------------------------
    def set_active_button(self, active_button):
        for button in self.bottom_buttons:
            button.setProperty("active", button == active_button)
            button.style().unpolish(button)
            button.style().polish(button)

    # -----------------------------
    # Open alerts dialog
    # -----------------------------
    def open_alerts_dialog(self):
        dlg = AlertsDialog(self.analytics_widget.alert_log, parent=self)
        dlg.exec()

    # -----------------------------
    # Export full telemetry DB to CSV
    # -----------------------------
    def export_db_to_csv(self):
        export_time = datetime.now()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Telemetry Database",
            f"telemetry_export_{export_time.strftime('%Y-%m-%d_%H-%M-%S')}.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not filename:
            return

        try:
            conn = sqlite3.connect("telemetry.db")
            conn.row_factory = sqlite3.Row

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # --- Host Info ---
                writer.writerow(["--- Host Info ---"])
                writer.writerow(["Exported at", export_time.strftime("%Y-%m-%d %H:%M:%S")])
                host = conn.execute("SELECT * FROM host LIMIT 1").fetchone()
                if host:
                    writer.writerow(["Hostname",         host["hostname"]])
                    writer.writerow(["OS",               f"{host['os_name']} {host['os_version']}"])
                    writer.writerow(["Machine",          host["machine"]])
                    writer.writerow(["CPU Model",        host["cpu_model"]])
                    writer.writerow(["CPU Cores",        host["cpu_core_count"]])
                    writer.writerow(["CPU Threads",      host["cpu_thread_count"]])
                    writer.writerow(["CPU Max MHz",      host["cpu_max_mhz"]])
                    writer.writerow(["Total RAM (GB)",   host["total_ram_gb"]])
                    writer.writerow(["GPU Detected",     "Yes" if host["gpu_detected"] else "No"])
                writer.writerow([])

                # --- Sessions ---
                writer.writerow(["--- Sessions ---"])
                writer.writerow(["Session ID", "Started At", "Sample Interval (ms)", "First Sample ID"])
                sessions = conn.execute("SELECT * FROM session ORDER BY session_id").fetchall()
                for s in sessions:
                    first_sample = conn.execute(
                        "SELECT MIN(sample_id) FROM sample WHERE session_id = ?", (s["session_id"],)
                    ).fetchone()[0]
                    writer.writerow([
                        s["session_id"],
                        s["started_at_iso"],
                        s["sample_interval_ms"],
                        first_sample if first_sample is not None else "—",
                    ])
                writer.writerow([])

                # --- Sample Data ---
                writer.writerow(["--- Sample Data ---"])
                writer.writerow([
                    "Timestamp", "Sample ID", "Session ID",
                    "CPU %", "CPU MHz",
                    "RAM %", "Swap %",
                    "GPU Util %", "GPU Mem %", "GPU Mem Used (MB)",
                    "GPU Temp (C)", "GPU Clock (MHz)", "GPU Power (W)", "GPU Power Limit (W)",
                    "Disk Read (B/s)", "Disk Write (B/s)",
                    "Disk Read Latency (ms)", "Disk Write Latency (ms)",
                    "Disk Usage %",
                ])

                sample_rows = conn.execute("""
                    SELECT
                        s.ts_iso, s.sample_id, s.session_id,
                        c.cpu_percent_total, c.freq_current_mhz,
                        r.ram_usage_percent, r.swap_usage_percent,
                        g.gpu_util_percent, g.gpu_mem_util_percent, g.gpu_mem_used_mb,
                        g.gpu_temp_c, g.gpu_core_clock_mhz,
                        g.gpu_power_usage_w, g.gpu_power_limit_w,
                        d.read_speed_bytes, d.write_speed_bytes,
                        d.avg_read_latency_ms, d.avg_write_latency_ms,
                        MAX(dp.usage_percent) AS disk_usage_percent
                    FROM sample s
                    LEFT JOIN cpu_sample            c  ON c.sample_id  = s.sample_id
                    LEFT JOIN ram_sample            r  ON r.sample_id  = s.sample_id
                    LEFT JOIN gpu_sample            g  ON g.sample_id  = s.sample_id AND g.gpu_id = 0
                    LEFT JOIN disk_io_sample        d  ON d.sample_id  = s.sample_id
                    LEFT JOIN disk_partition_sample dp ON dp.sample_id = s.sample_id
                    GROUP BY s.sample_id
                    ORDER BY s.session_id, s.sample_id
                """).fetchall()

                def fmt(v):
                    if v is None:
                        return "N/A"
                    return f"{v:.2f}" if isinstance(v, float) else v

                for row in sample_rows:
                    writer.writerow([
                        row["ts_iso"], row["sample_id"], row["session_id"],
                        fmt(row["cpu_percent_total"]), fmt(row["freq_current_mhz"]),
                        fmt(row["ram_usage_percent"]), fmt(row["swap_usage_percent"]),
                        fmt(row["gpu_util_percent"]), fmt(row["gpu_mem_util_percent"]),
                        fmt(row["gpu_mem_used_mb"]),
                        fmt(row["gpu_temp_c"]), fmt(row["gpu_core_clock_mhz"]),
                        fmt(row["gpu_power_usage_w"]), fmt(row["gpu_power_limit_w"]),
                        fmt(row["read_speed_bytes"]), fmt(row["write_speed_bytes"]),
                        fmt(row["avg_read_latency_ms"]), fmt(row["avg_write_latency_ms"]),
                        fmt(row["disk_usage_percent"]),
                    ])

            conn.close()
            QMessageBox.information(self, "Export Complete",
                                    f"Database exported successfully to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export database:\n{e}")

    # -----------------------------
    # Open settings
    # -----------------------------
    def open_settings(self):
        self.settings_window = SettingsWindow(parent=self)
        self.settings_window.exec()  # modal window



# -----------------------------
# Settings
# -----------------------------
class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 250)
        self.parent = parent  # reference to main dashboard

        layout = QVBoxLayout()

        # ---------------------------
        # Graph refresh rate
        # ---------------------------
        layout.addWidget(QLabel("Graph Refresh Rate (ms):"))
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(100, 10000)
        self.refresh_spin.setSingleStep(100)

        # Load the current refresh rate from the live monitor
        self.refresh_spin.setValue(self.parent.live_monitor_widget.graph_refresh_rate)
        layout.addWidget(self.refresh_spin)

        # ---------------------------
        # Accent Colour
        # ---------------------------
        layout.addWidget(QLabel("Accent Colour (Restart Required):"))
        
        # Hex input field
        current_color = self.parent.settings_data.get("accent_colour")
        self.hex_input = QLineEdit(current_color)
        self.hex_input.setMaxLength(7)
        self.hex_input.setFixedWidth(100)
        self.hex_input.setPlaceholderText("#RRGGBB")

        layout.addWidget(self.hex_input)
        layout.addStretch()

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save_settings(self):
        # Update live monitor refresh rate
        new_rate = self.refresh_spin.value()
        hex_code = self.hex_input.text().strip().upper()
        live_monitor = self.parent.live_monitor_widget

        # Validate hex code
        if not QColor(hex_code).isValid():
            QMessageBox.warning(self, "Invalid Color", "Please enter a valid hex color (e.g. #1A2B3C)")
            return
        
        # Apply new settings
        live_monitor.graph_refresh_rate = new_rate
        live_monitor.update_timer.setInterval(new_rate)
        live_monitor.accent_colour = hex_code


        # Update settings data
        self.parent.settings_data["graph_refresh_rate"] = new_rate
        self.parent.settings_data["accent_colour"] = hex_code
        save_settings(self.parent.settings_data)

        self.close()



# -----------------------------
# Main Entry Point
# -----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load Inter font (Regular + Bold weights so font-weight: bold renders correctly)
    for font_file in [
        "dashboard_service/assets/fonts/Inter/Inter_28pt-Regular.ttf",
        "dashboard_service/assets/fonts/Inter/Inter_28pt-Bold.ttf",
        "dashboard_service/assets/fonts/Inter/Inter_28pt-ExtraBold.ttf",
    ]:
        QFontDatabase.addApplicationFont(font_file)

    font_id = QFontDatabase.addApplicationFont(
        "dashboard_service/assets/fonts/Inter/Inter_28pt-Regular.ttf"
    )
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(font_family))

    # Load QSS stylesheet
    with open("dashboard_service/assets/styles/style.qss", "r") as f:
        style = f.read()
        
    # Apply accent colour from settings
    settings = load_settings()
    accent_colour = settings.get("accent_colour")
    style = style.replace("ACCENT_COLOUR", accent_colour)
    app.setStyleSheet(style)

    # Start main window
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
