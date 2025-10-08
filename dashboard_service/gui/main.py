# dashboard_service/gui/main.py
# Author: Andrew Fox

# -----------------------------
# Imports
# -----------------------------
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont

# -----------------------------
# Main Window
# -----------------------------
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
        # Top Bar Section
        # -----------------------------
        self.top_bar()

        # -----------------------------
        # Content Area Section
        # -----------------------------
        self.content_area()

        # -----------------------------
        # Initialize content widgets (placeholders)
        # -----------------------------
        self.content_widgets = {
            "Live System Monitoring": QLabel("Live System Monitoring Panel"),
            "Analytics": QLabel("Analytics Panel"),
            "RAM Cleaner": QLabel("RAM Cleaner Panel"),
            "Performance Mode": QLabel("Performance Mode Panel")
        }

        # Add all widgets to layout and hide initially
        for widget in self.content_widgets.values():
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(widget)
            widget.hide()

        # -----------------------------
        # Bottom Navigation Section
        # -----------------------------
        self.bottom_bar()

        # -----------------------------
        # Set default mode: Live Monitoring
        # -----------------------------
        self.set_active_button(self.live_button)
        self.content_widgets["Live System Monitoring"].show()

    # -----------------------------
    # Top Bar Section
    # -----------------------------
    def top_bar(self):
        self.top_bar = QFrame()
        self.top_layout = QHBoxLayout()
        self.top_bar.setLayout(self.top_layout)
        self.main_layout.addWidget(self.top_bar)

        # Left: Title
        self.top_layout.addWidget(QLabel("Smart Dashboard"), stretch=1)

        # Right: Buttons
        self.alerts_button = QPushButton("Alerts")
        self.settings_button = QPushButton("Settings")
        for button in [self.alerts_button, self.settings_button]:
            button.setObjectName("topButton")
            button.setFixedSize(80, 40)
            self.top_layout.addWidget(button)

    # -----------------------------
    # Content Area Section
    # -----------------------------
    def content_area(self):
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout()
        self.content_frame.setLayout(self.content_layout)
        self.main_layout.addWidget(self.content_frame, stretch=1)

    # -----------------------------
    # Bottom Navigation Section
    # -----------------------------
    def bottom_bar(self):
        self.bottom_bar = QFrame()
        self.bottom_layout = QHBoxLayout()
        self.bottom_bar.setLayout(self.bottom_layout)
        self.main_layout.addWidget(self.bottom_bar)

        # Buttons
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
        # Hide all panels first
        self.hide_all_content_widgets()

        # Show the selected panel
        self.content_widgets[mode_name].show()

        # Update active button
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
    # Hide all content widgets
    # -----------------------------
    def hide_all_content_widgets(self):
        for widget in self.content_widgets.values():
            widget.hide()

# -----------------------------
# Main
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
