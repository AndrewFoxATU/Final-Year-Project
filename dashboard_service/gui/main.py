# dashboard_service/gui/main.py
# Author: Andrew Fox

# -----------------------------
# Imports
# -----------------------------
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont
import pyqtgraph as pg


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

        # Top Bar
        self.top_bar()

        # Content Area
        self.content_area()

        # Initialize Sections (CPU, GPU, RAM, Storage)
        self.create_sections()

        # Arrange Sections in 2x2 Grid
        self.arrange_sections()

        # Bottom Navigation Bar
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

        self.alerts_button = QPushButton("Alerts")
        self.settings_button = QPushButton("Settings")

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
    # Create Sections
    # -----------------------------
    def create_sections(self):
        # Define what info each section displays
        self.sections = {
            "CPU": {"fields": ["Usage", "Clock", "Temp"]},
            "GPU": {"fields": ["Usage", "Clock", "Temp"]},
            "RAM": {"fields": ["Usage"]},
            "Storage": {"fields": ["Usage"]}
        }

        self.section_frames = {}
        for name, config in self.sections.items():
            frame, curve, data = self.create_section(name, config["fields"])
            self.section_frames[name] = (frame, curve, data)

    # -----------------------------
    # Create Section (Dynamic)
    # -----------------------------
    def create_section(self, name, fields):
        layout = QHBoxLayout()

        # Info layout (labels)
        info_layout = QVBoxLayout()
        section_title = QLabel(f"<b>{name}</b>")
        section_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        info_layout.addWidget(section_title)

        labels = {}
        for field in fields:
            if field == "Usage":
                label = QLabel("Usage: 0%")
            elif field == "Clock":
                label = QLabel("Clock: 0 MHz")
            elif field == "Temp":
                label = QLabel("Temp: 0°C")
            else:
                label = QLabel(f"{field}: 0")

            # Align labels to the right
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
            info_layout.addWidget(label)
            labels[field] = label

        info_layout.addStretch()

        # Graph for data visualization
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('#2a2a2a')

        # Hide axis numbers and labels
        plot_widget.getAxis('bottom').setTicks([])
        plot_widget.getAxis('left').setTicks([])
        plot_widget.getAxis('bottom').setStyle(showValues=False)
        plot_widget.getAxis('left').setStyle(showValues=False)
        plot_widget.setLabel('left', '')
        plot_widget.setLabel('bottom', '')

        # Add grid for visual consistency
        plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Allow graph to scale with window
        from PyQt6.QtWidgets import QSizePolicy
        plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        curve = plot_widget.plot([], [], pen=pg.mkPen(color='r', width=2))

        # Layout balance: keep text narrow, graph wide
        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(plot_widget, stretch=4)

        frame = QFrame()
        frame.setLayout(layout)
        frame.curve = curve
        frame.data = [0] * 50
        frame.labels = labels

        return frame, curve, frame.data

    # -----------------------------
    # Arrange Sections in Grid
    # -----------------------------
    def arrange_sections(self):
        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        grid_widget.setLayout(grid_layout)

        names = list(self.section_frames.keys())

        grid_layout.addWidget(self.section_frames[names[0]][0], 0, 0)
        grid_layout.addWidget(self.section_frames[names[1]][0], 0, 1)
        grid_layout.addWidget(self.section_frames[names[2]][0], 1, 0)
        grid_layout.addWidget(self.section_frames[names[3]][0], 1, 1)

        self.content_widgets = {
            "Live System Monitoring": grid_widget,
            "Analytics": QLabel("Analytics Panel"),
            "RAM Cleaner": QLabel("RAM Cleaner Panel"),
            "Performance Mode": QLabel("Performance Mode Panel")
        }

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
