# dashboard_service/gui/main.py
# Author: Andrew Fox
# Run with: python -m dashboard_service.gui.main
# -----------------------------
# Imports
# -----------------------------
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGridLayout, QSizePolicy, QDialog,
    QComboBox, QSpinBox, QColorDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontDatabase, QFont, QCursor
import pyqtgraph as pg

# Import the Live System Monitoring panel
from dashboard_service.gui.live_monitor import LiveSystemMonitor
# Import settings manager
from dashboard_service.gui.settings_manager import load_settings, save_settings


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

    # -----------------------------
    # Top Bar
    # -----------------------------
    def top_bar(self):
        self.top_bar = QFrame()
        self.top_layout = QHBoxLayout()
        self.top_bar.setLayout(self.top_layout)
        self.main_layout.addWidget(self.top_bar)

        title = QLabel("Smart Dashboard")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.top_layout.addWidget(title, stretch=1)

        # Alerts & Settings buttons
        self.alerts_button = QPushButton("Alerts")
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        
        for button in [self.alerts_button, self.settings_button]:
            button.setObjectName("topButton")
            button.setFixedSize(80, 40)
            self.top_layout.addWidget(button)

    # -----------------------------
    # Content Area
    # -----------------------------
    def content_area(self):
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout()
        self.content_frame.setLayout(self.content_layout)
        self.main_layout.addWidget(self.content_frame, stretch=1)

    # -----------------------------
    # Arrange Sections (Panels)
    # -----------------------------
    def arrange_sections(self):
        # Import and use LiveSystemMonitor as a self-contained widget
        self.live_monitor_widget = LiveSystemMonitor(self)

        # Create main content mapping
        self.content_widgets = {
            "Live System Monitoring": self.live_monitor_widget,
            "Analytics": QLabel("Analytics Panel"),
            "RAM Cleaner": QLabel("RAM Cleaner Panel"),
            "Performance Mode": QLabel("Performance Mode Panel")
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
        self.bottom_layout = QHBoxLayout()
        self.bottom_bar.setLayout(self.bottom_layout)
        self.main_layout.addWidget(self.bottom_bar)

        # Navigation buttons
        self.live_button = QPushButton("Live System Monitoring")
        self.analytics_button = QPushButton("Analytics")
        self.ram_button = QPushButton("RAM Cleaner")
        self.performance_button = QPushButton("Performance Mode")

        self.bottom_buttons = [
            self.live_button,
            self.analytics_button,
            self.ram_button,
            self.performance_button
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
            "RAM Cleaner": self.ram_button,
            "Performance Mode": self.performance_button
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
        self.setFixedSize(200, 200)
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
        layout.addWidget(QLabel("Accent Colour:"))

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save_settings(self):
        # Update live monitor refresh rate
        new_rate = self.refresh_spin.value()
        live_monitor = self.parent.live_monitor_widget

        live_monitor.graph_refresh_rate = new_rate
        live_monitor.update_timer.setInterval(new_rate)

        # Update settings data
        self.parent.settings_data["graph_refresh_rate"] = new_rate
        save_settings(self.parent.settings_data)

        self.close()



# -----------------------------
# Main Entry Point
# -----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load Inter font
    font_id = QFontDatabase.addApplicationFont(
        "dashboard_service/assets/fonts/Inter/Inter_28pt-Regular.ttf"
    )
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(font_family))

    # Load QSS stylesheet
    with open("dashboard_service/assets/styles/style.qss", "r") as f:
        app.setStyleSheet(f.read())

    # Start main window
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
