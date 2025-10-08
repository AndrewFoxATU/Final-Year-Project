# dashboard_service/gui/main.py
# Author: Andrew Fox

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart System Performance Dashboard")
        self.setGeometry(100, 100, 1200, 700)

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # -----------------------------
        # Top bar frame
        # -----------------------------
        self.top_bar = QFrame()
        self.top_layout = QHBoxLayout()
        self.top_bar.setLayout(self.top_layout)
        self.main_layout.addWidget(self.top_bar)

        # Top-left placeholder (window title space)
        self.top_layout.addWidget(QLabel("Smart Dashboard"), stretch=1)

        # Top-right buttons: Alerts & Settings
        self.alerts_btn = QPushButton("Alerts")
        self.settings_btn = QPushButton("Settings")
        for btn in [self.alerts_btn, self.settings_btn]:
            btn.setObjectName("topButton")
            btn.setFixedSize(80, 40)
            self.top_layout.addWidget(btn)

        # -----------------------------
        # Main content area
        # -----------------------------
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout()
        self.content_frame.setLayout(self.content_layout)
        self.main_layout.addWidget(self.content_frame, stretch=1)

        # Placeholder label for main content
        self.content_label = QLabel("Main Content Area")
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.content_label)

        # -----------------------------
        # Bottom navigation bar
        # -----------------------------
        self.bottom_bar = QFrame()
        self.bottom_layout = QHBoxLayout()
        self.bottom_bar.setLayout(self.bottom_layout)
        self.main_layout.addWidget(self.bottom_bar)

        # Bottom buttons
        self.live_btn = QPushButton("Live System Monitoring")
        self.analytics_btn = QPushButton("Analytics")
        self.ram_btn = QPushButton("RAM Cleaner")
        self.performance_btn = QPushButton("Performance Mode")

        self.bottom_buttons = [
            self.live_btn,
            self.analytics_btn,
            self.ram_btn,
            self.performance_btn
        ]

        # Set object names and minimum height for styling
        for btn in self.bottom_buttons:
            btn.setObjectName("bottomButton")
            btn.setMinimumHeight(50)
            self.bottom_layout.addWidget(btn)

        # Connect buttons to mode switching
        self.live_btn.clicked.connect(lambda: self.switch_mode("Live System Monitoring"))
        self.analytics_btn.clicked.connect(lambda: self.switch_mode("Analytics"))
        self.ram_btn.clicked.connect(lambda: self.switch_mode("RAM Cleaner"))
        self.performance_btn.clicked.connect(lambda: self.switch_mode("Performance Mode"))

        # Set default active button
        self.set_active_button(self.live_btn)

    # -----------------------------
    # Mode switching
    # -----------------------------
    def switch_mode(self, mode_name):
        self.content_label.setText(f"{mode_name} Panel")

        # Map mode name to button
        mapping = {
            "Live System Monitoring": self.live_btn,
            "Analytics": self.analytics_btn,
            "RAM Cleaner": self.ram_btn,
            "Performance Mode": self.performance_btn
        }
        self.set_active_button(mapping[mode_name])

    def set_active_button(self, active_button):
        """Set the bottom navigation button active state"""
        for btn in self.bottom_buttons:
            if btn == active_button:
                btn.setProperty("active", True)
            else:
                btn.setProperty("active", False)
            # Refresh style
            btn.style().unpolish(btn)
            btn.style().polish(btn)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # -----------------------------
    # Load Inter font
    # -----------------------------
    font_id = QFontDatabase.addApplicationFont(
        "dashboard_service/assets/fonts/Inter/Inter_28pt-Regular.ttf"
    )
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(font_family))

    # -----------------------------
    # Load QSS stylesheet
    # -----------------------------
    with open("dashboard_service/assets/styles/style.qss", "r") as f:
        app.setStyleSheet(f.read())

    # Start main window
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
