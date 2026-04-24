# dashboard_service/gui/analytics_view.py
# Author: Andrew Fox


# -----------------------------
# Imports
# -----------------------------
import csv
import sqlite3
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QPushButton,
    QFileDialog, QDialog, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

from dashboard_service.gui.settings_manager import load_settings
from analytics_service.analytics.features import FeatureExtractor, WINDOW_SIZE
from analytics_service.analytics.labels import LABEL_COMPONENTS
from analytics_service.analytics.model import PerformanceModel


# -----------------------------
# Issue metadata
# -----------------------------
ISSUE_META = {
    "cpu_thermal_throttle":    ("Thermal Throttling",
                                "Your CPU is getting too hot and slowing itself down to prevent damage.",
                                "Check that your PC vents are clear and all fans are spinning. Cleaning out dust from the heatsink usually helps."),
    "cpu_bottleneck":          ("CPU Bottleneck",
                                "Your CPU is running at full capacity and holding back the rest of your system.",
                                "Open Task Manager and close any programs using a lot of CPU that you don't need."),
    "cpu_sustained_high_load": ("Sustained High CPU Load",
                                "Your CPU has been under heavy load for an extended period with no relief.",
                                "Check Task Manager for a process consuming excessive CPU and close or restart it if possible."),
    "ram_pressure":            ("RAM Pressure",
                                "Your system is almost out of memory.",
                                "Close applications you are not actively using. If this happens regularly, consider upgrading your RAM."),
    "ram_memory_leak":         ("Memory Leak Detected",
                                "A running program appears to be gradually consuming more and more memory without releasing it.",
                                "Restart the application that is growing in memory usage. Check for available updates, as this is often a software bug."),
    "excessive_swap_usage":    ("Excessive Swap Usage",
                                "Your system has run out of RAM and is using your disk as overflow memory, which is much slower.",
                                "Close unused applications to free up RAM. Adding more physical RAM is the permanent fix."),
    "disk_full":               ("Disk Nearly Full",
                                "One of your drives is almost out of storage space.",
                                "Delete files you no longer need and empty the Recycle Bin. Moving files to an external drive also helps."),
    "disk_bottleneck":         ("Disk I/O Bottleneck",
                                "Your disk is being pushed to its maximum read or write speed, causing slowdowns.",
                                "Avoid running multiple large file operations at the same time. Upgrading to an SSD will significantly improve this."),
    "disk_high_latency":       ("High Disk Latency",
                                "Your disk is taking longer than normal to respond to requests.",
                                "Run a disk health check using Windows tools. On older hard drives this can be an early warning sign — back up your data soon."),
    "gpu_overheating":         ("GPU Overheating",
                                "Your graphics card is running at a dangerously high temperature.",
                                "Make sure your PC case has good airflow and clean dust from the GPU fans. Lowering graphics settings will also reduce heat."),
    "gpu_power_throttle":      ("GPU Power Throttle",
                                "Your GPU is hitting its power limit and reducing its performance to stay within it.",
                                "Ensure your power supply is adequate for your GPU. You can also check GPU power limit settings in your driver software."),
    "gpu_vram_pressure":       ("VRAM Pressure",
                                "Your graphics card is almost out of video memory.",
                                "Lower texture quality or resolution in your application. Closing other GPU-intensive programs will free up VRAM."),
}

_SAMPLE_QUERY = """
    SELECT
        c.cpu_percent_total, c.freq_current_mhz,
        r.ram_usage_percent, r.swap_usage_percent,
        g.gpu_util_percent, g.gpu_mem_util_percent,
        g.gpu_temp_c, g.gpu_core_clock_mhz,
        g.gpu_power_usage_w, g.gpu_power_limit_w,
        d.avg_read_latency_ms, d.avg_write_latency_ms,
        d.read_speed_bytes, d.write_speed_bytes,
        MAX(dp.usage_percent) AS disk_usage_percent
    FROM sample s
    LEFT JOIN cpu_sample            c  ON c.sample_id  = s.sample_id
    LEFT JOIN ram_sample            r  ON r.sample_id  = s.sample_id
    LEFT JOIN disk_io_sample        d  ON d.sample_id  = s.sample_id
    LEFT JOIN disk_partition_sample dp ON dp.sample_id = s.sample_id
    LEFT JOIN gpu_sample            g  ON g.sample_id  = s.sample_id AND g.gpu_id = 0
    WHERE s.session_id = ?
    GROUP BY s.sample_id
    ORDER BY s.ts_unix_ms DESC
    LIMIT ?
"""


# -----------------------------
# Analytics Thread
# -----------------------------
class AnalyticsThread(QThread):

    status_signal     = pyqtSignal(str, int)   # (status_text, sample_count)
    prediction_signal = pyqtSignal(dict, list)  # (component_risks 0–1, issues list)

    MIN_SAMPLES = 200
    INTERVAL_MS = 5000

    def run(self):
        try:
            conn = sqlite3.connect("telemetry.db")
            conn.row_factory = sqlite3.Row
        except Exception:
            self.status_signal.emit("DB unavailable", 0)
            return

        try:
            model = PerformanceModel()
        except Exception:
            self.status_signal.emit("Model not found", 0)
            conn.close()
            return

        session_id = conn.execute("SELECT MAX(session_id) FROM session").fetchone()[0]
        if session_id is None:
            self.status_signal.emit("No session", 0)
            conn.close()
            return

        while not self.isInterruptionRequested():
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM sample WHERE session_id = ?", (session_id,)
                ).fetchone()[0]

                if count < self.MIN_SAMPLES:
                    self.status_signal.emit("Collecting\u2026", count)
                    self.msleep(1000)
                    continue

                self.status_signal.emit("Ready", count)

                rows = conn.execute(_SAMPLE_QUERY, (session_id, WINDOW_SIZE)).fetchall()
                samples = [dict(r) for r in rows]
                features = FeatureExtractor.compute(samples)

                if features is None:
                    self.msleep(self.INTERVAL_MS)
                    continue

                result = model.predict(features)

                # Convert 0/1/2 risk levels → 0.0 / 0.5 / 1.0 for progress bars
                component_risks = {k: v / 2.0 for k, v in result["component_risks"].items()}

                fired_set = set(result["issues"])
                issues = []
                for label, (title, description, fix) in ISSUE_META.items():
                    issues.append({
                        "component":   LABEL_COMPONENTS.get(label, "Other"),
                        "title":       title,
                        "probability": result["probabilities"].get(label, 0.0),
                        "description": description,
                        "fix":         fix,
                        "fired":       label in fired_set,
                    })

                self.prediction_signal.emit(component_risks, issues)

            except Exception:
                pass

            self.msleep(self.INTERVAL_MS)

        conn.close()


# -----------------------------
# Alerts Dialog
# -----------------------------
class AlertsDialog(QDialog):

    def __init__(self, alert_log, parent=None):
        super().__init__(parent)
        self.alert_log = alert_log

        self.setWindowTitle("Alert Log")
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        self.setLayout(layout)

        header_row = QHBoxLayout()
        header_lbl = QLabel("<b>Alert Log</b>")
        header_lbl.setObjectName("cardHeader")
        count_lbl = QLabel(f"{len(alert_log)} alert(s) this session")
        count_lbl.setObjectName("statCardSub")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_row.addWidget(header_lbl, stretch=1)
        header_row.addWidget(count_lbl)
        layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("issuesContainer")
        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(6)
        inner.setAlignment(Qt.AlignmentFlag.AlignTop)
        container.setLayout(inner)

        if not alert_log:
            empty = QLabel("No alerts logged this session.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("noIssuesLabel")
            inner.addWidget(empty)
        else:
            for entry in reversed(alert_log):
                row_frame = QFrame()
                row_frame.setObjectName("sectionFrame")
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(10, 6, 10, 6)
                row_layout.setSpacing(10)
                row_frame.setLayout(row_layout)

                time_lbl = QLabel(entry["time"].strftime("%H:%M:%S"))
                time_lbl.setObjectName("sessionLabel")
                time_lbl.setFixedWidth(60)

                badge = QLabel(entry["component"])
                badge.setFixedWidth(55)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setObjectName("issueBadge")

                title_lbl = QLabel(entry["title"])

                prob_lbl = QLabel(f"{entry['probability']:.0%}")
                prob_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                prob_lbl.setObjectName("issueProb")

                row_layout.addWidget(time_lbl)
                row_layout.addWidget(badge)
                row_layout.addWidget(title_lbl, stretch=1)
                row_layout.addWidget(prob_lbl)

                inner.addWidget(row_frame)

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)


# -----------------------------
# Export Data
# -----------------------------
class ExportData(QDialog):

    def __init__(self, session_summary, current_issues, parent=None):
        super().__init__(parent)
        self.session_summary = session_summary
        self.current_issues = current_issues

        self.setWindowTitle("Export Data")
        self.setFixedWidth(380)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        self.setLayout(layout)

        layout.addWidget(QLabel("<b>Select data to export</b>"))

        self.chk_summary = QCheckBox("Session Summary")
        self.chk_summary.setChecked(True)

        self.chk_issues = QCheckBox("Detected Issues")
        self.chk_issues.setChecked(bool(current_issues))
        self.chk_issues.setEnabled(bool(current_issues))

        self.chk_metrics = QCheckBox("Collected Metrics  (coming soon)")
        self.chk_metrics.setChecked(False)
        self.chk_metrics.setEnabled(False)

        for chk in (self.chk_summary, self.chk_issues, self.chk_metrics):
            layout.addWidget(chk)

        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self.reject)

        export_btn = QPushButton("Export")
        export_btn.setFixedHeight(34)
        export_btn.setObjectName("accentButton")
        export_btn.clicked.connect(self.do_export)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)

    def do_export(self):
        if not self.chk_summary.isChecked() and not self.chk_issues.isChecked():
            QMessageBox.warning(self, "Nothing selected",
                                "Please select at least one section to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Export",
            f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not filename:
            return

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if self.chk_summary.isChecked():
                writer.writerow(["=== Session Summary ==="])
                writer.writerow(["Exported at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                for key, value in self.session_summary.items():
                    writer.writerow([key, value])
                writer.writerow([])

            if self.chk_issues.isChecked() and self.current_issues:
                writer.writerow(["=== Detected Issues ==="])
                writer.writerow(["Component", "Issue", "Probability", "Description"])
                for issue in sorted(self.current_issues, key=lambda x: x["probability"], reverse=True):
                    writer.writerow([
                        issue["component"],
                        issue["title"],
                        f"{issue['probability']:.0%}",
                        issue["description"],
                    ])
                writer.writerow([])

        self.accept()


# -----------------------------
# Analytics Widget
# -----------------------------
class AnalyticsWidget(QWidget):

    MIN_SAMPLES_REQUIRED = 200

    def __init__(self, parent=None):
        super().__init__(parent)


        # Load settings
        settings = load_settings()
        self.accent_colour = settings.get("accent_colour")

        self.running = False
        self.session_start = None
        self.predictions_count = 0
        self.session_issues_count = 0
        self.current_issues = []
        self.health_score = 0
        self._thread = None
        self.alert_log = []
        self._prev_fired = set()

        # Layout
        outer = QVBoxLayout()
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)
        self.setLayout(outer)

        outer.addWidget(self.create_header())
        outer.addWidget(self.create_kpi_row())
        outer.addWidget(self.create_issues_panel(), stretch=1)

        # Timers
        self.session_timer = QTimer()
        self.session_timer.setInterval(1000)
        self.session_timer.timeout.connect(self.tick_session)

    # -----------------------------
    # Create Header
    # -----------------------------
    def create_header(self):
        bar = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        bar.setLayout(layout)

        title = QLabel("<b>ML Performance Analytics</b>")
        title.setObjectName("analyticsTitle")

        self.export_btn = QPushButton("Export Data")
        self.export_btn.setFixedSize(120, 36)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.open_export_dialog)

        self.toggle_btn = QPushButton("Start Analytics")
        self.toggle_btn.setFixedSize(140, 36)
        self.toggle_btn.setObjectName("accentButton")
        self.toggle_btn.clicked.connect(self.toggle)

        layout.addWidget(title, stretch=1)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.toggle_btn)

        return bar

    # -----------------------------
    # Create KPI Row
    # -----------------------------
    def create_kpi_card(self, title):
        frame = QFrame()
        frame.setObjectName("sectionFrame")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        frame.setLayout(layout)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("statCardTitle")

        frame.value_label = QLabel("—")
        frame.value_label.setObjectName("statCardValue")

        frame.sub_label = QLabel("")
        frame.sub_label.setObjectName("statCardSub")
        frame.sub_label.setWordWrap(True)
        frame.sub_label.setVisible(False)

        layout.addWidget(title_lbl)
        layout.addWidget(frame.value_label)
        layout.addWidget(frame.sub_label)

        return frame

    def create_kpi_row(self):
        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        row.setLayout(layout)

        self.card_health = self.create_kpi_card("System Health Score")
        self.card_status = self.create_kpi_card("Model Status")

        self.set_kpi(self.card_health, "—", "/ 100")
        self.set_kpi(self.card_status, "Stopped")

        layout.addWidget(self.card_health, stretch=1)
        layout.addWidget(self.create_session_bar(), stretch=3)
        layout.addWidget(self.card_status, stretch=1)

        return row

    # -----------------------------
    # Create Session Bar
    # -----------------------------
    def create_session_bar(self):
        frame = QFrame()
        frame.setObjectName("sectionFrame")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(0)
        frame.setLayout(layout)

        def stat_block(label_text):
            block = QWidget()
            bl = QVBoxLayout()
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(2)
            block.setLayout(bl)
            lbl = QLabel(label_text)
            lbl.setObjectName("sessionLabel")
            val = QLabel("—")
            val.setObjectName("sessionValue")
            bl.addWidget(lbl)
            bl.addWidget(val)
            return block, val

        def divider():
            d = QFrame()
            d.setFrameShape(QFrame.Shape.VLine)
            d.setObjectName("sessionDivider")
            d.setFixedWidth(1)
            return d

        block_time,  self.sess_time_val  = stat_block("Running for")
        block_preds, self.sess_preds_val = stat_block("Predictions made")
        block_flags, self.sess_flags_val = stat_block("Issues flagged")

        layout.addWidget(block_time, stretch=1)
        layout.addWidget(divider())
        layout.addSpacing(16)
        layout.addWidget(block_preds, stretch=1)
        layout.addWidget(divider())
        layout.addSpacing(16)
        layout.addWidget(block_flags, stretch=1)

        return frame

    # -----------------------------
    # Create Issues Panel
    # -----------------------------
    def create_issues_panel(self):
        frame = QFrame()
        frame.setObjectName("sectionFrame")

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        frame.setLayout(layout)

        header = QLabel("<b>Detected Issues</b>")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.issues_container = QWidget()
        self.issues_container.setObjectName("issuesContainer")
        self.issues_layout = QVBoxLayout()
        self.issues_layout.setContentsMargins(0, 0, 0, 0)
        self.issues_layout.setSpacing(8)
        self.issues_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.issues_container.setLayout(self.issues_layout)

        self.scroll_area.setWidget(self.issues_container)
        layout.addWidget(self.scroll_area, stretch=1)

        self.no_issues_label = QLabel("No issues detected.")
        self.no_issues_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_issues_label.setObjectName("noIssuesLabel")
        self.issues_layout.addWidget(self.no_issues_label)

        return frame

    # -----------------------------
    # Start / Stop Toggle
    # -----------------------------
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        self.running = True
        self.session_start = datetime.now()
        self.predictions_count = 0
        self.session_issues_count = 0
        self.current_issues = []
        self.alert_log = []
        self._prev_fired = set()
        self.session_timer.start()
        self.export_btn.setEnabled(True)
        self.toggle_btn.setText("Stop Analytics")
        self.set_kpi(self.card_status, "Collecting\u2026", f"0 / {self.MIN_SAMPLES_REQUIRED} samples")
        self.sess_time_val.setText("0s")
        self.sess_preds_val.setText("0")
        self.sess_flags_val.setText("0")

        self._thread = AnalyticsThread(self)
        self._thread.status_signal.connect(self.update_status)
        self._thread.prediction_signal.connect(self.update_predictions)
        self._thread.start()

    def stop(self):
        self.running = False
        self.session_timer.stop()
        self.session_start = None
        self.toggle_btn.setText("Start Analytics")
        if self._thread is not None:
            self._thread.requestInterruption()
            self._thread.wait()
            self._thread = None
        self.reset_display()

    def shutdown(self):
        """Called on app close to cleanly stop the thread."""
        if self._thread is not None:
            self._thread.requestInterruption()
            self._thread.wait()
            self._thread = None

    def reset_display(self):
        self.set_kpi(self.card_health, "—", "/ 100")
        self.set_kpi(self.card_status, "Stopped")
        self.sess_time_val.setText("—")
        self.sess_preds_val.setText("—")
        self.sess_flags_val.setText("—")
        self.current_issues = []
        self.export_btn.setEnabled(False)
        self.clear_issues()
        self.no_issues_label.setVisible(True)

    # -----------------------------
    # Session Tick
    # -----------------------------
    def tick_session(self):
        if self.session_start is None:
            return
        elapsed = int((datetime.now() - self.session_start).total_seconds())
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            self.sess_time_val.setText(f"{hours}h {minutes}m {seconds}s")
        elif minutes > 0:
            self.sess_time_val.setText(f"{minutes}m {seconds}s")
        else:
            self.sess_time_val.setText(f"{seconds}s")

    # -----------------------------
    # Export Dialog
    # -----------------------------
    def open_export_dialog(self):
        elapsed_str = "—"
        if self.session_start:
            elapsed = int((datetime.now() - self.session_start).total_seconds())
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                elapsed_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                elapsed_str = f"{minutes}m {seconds}s"
            else:
                elapsed_str = f"{seconds}s"

        summary = {
            "Running for":            elapsed_str,
            "Predictions made":       self.predictions_count,
            "Issues flagged (total)": self.session_issues_count,
            "System health score":    f"{self.health_score} / 100",
        }

        dlg = ExportData(summary, self.current_issues, parent=self)
        dlg.exec()

    # -----------------------------
    # Helpers
    # -----------------------------
    def set_kpi(self, card, value, sub=""):
        card.value_label.setText(value)
        card.sub_label.setText(sub)
        card.sub_label.setVisible(bool(sub))

    def clear_issues(self):
        for i in reversed(range(self.issues_layout.count())):
            item = self.issues_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget and widget is not self.no_issues_label:
                widget.deleteLater()
                self.issues_layout.removeItem(item)

    # -----------------------------
    # Public Update API
    # -----------------------------
    def update_status(self, status_text, sample_count=0):
        if not self.running:
            return
        if "Ready" in status_text or "ready" in status_text:
            self.set_kpi(self.card_status, "Ready", f"{sample_count:,} samples")
        else:
            self.set_kpi(self.card_status, status_text, f"{sample_count} / {self.MIN_SAMPLES_REQUIRED} samples")

    def update_predictions(self, component_risks, issues):
        if not self.running:
            return

        fired_issues = [i for i in issues if i["fired"]]
        self.predictions_count += 1
        self.session_issues_count += len(fired_issues)
        self.current_issues = list(issues)

        now = datetime.now()
        current_fired_titles = {i["title"] for i in fired_issues}
        for issue in fired_issues:
            if issue["title"] not in self._prev_fired:
                self.alert_log.append({
                    "time":        now,
                    "title":       issue["title"],
                    "component":   issue["component"],
                    "probability": issue["probability"],
                })
        self._prev_fired = current_fired_titles
        self.sess_preds_val.setText(f"{self.predictions_count:,}")
        self.sess_flags_val.setText(f"{self.session_issues_count:,}")
        self.export_btn.setEnabled(True)

        overall = max(component_risks.values(), default=0.0)
        self.health_score = int((1.0 - overall) * 100)
        self.set_kpi(self.card_health, str(self.health_score), "/ 100")

        self.clear_issues()
        self.no_issues_label.setVisible(False)

        for issue in sorted(issues, key=lambda x: x["probability"], reverse=True):
            card = QFrame()
            card.setObjectName("sectionFrame")

            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(4)
            card.setLayout(card_layout)

            title_row = QHBoxLayout()

            badge = QLabel(issue["component"])
            badge.setFixedWidth(55)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setObjectName("issueBadge" if issue["fired"] else "issueBadgeMuted")

            name_lbl = QLabel(f"<b>{issue['title']}</b>")

            prob_lbl = QLabel(f"Confidence: {issue['probability']:.0%}")
            prob_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            prob_lbl.setObjectName("issueProb" if issue["fired"] else "issueProbMuted")

            title_row.addWidget(badge)
            title_row.addWidget(name_lbl, stretch=1)
            title_row.addWidget(prob_lbl)

            desc_lbl = QLabel(issue["description"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setObjectName("issueDesc")

            card_layout.addLayout(title_row)
            card_layout.addWidget(desc_lbl)

            if issue["fired"]:
                fix_lbl = QLabel(f"Fix: {issue['fix']}")
                fix_lbl.setWordWrap(True)
                fix_lbl.setObjectName("issueFix")
                card_layout.addWidget(fix_lbl)

            self.issues_layout.addWidget(card)
