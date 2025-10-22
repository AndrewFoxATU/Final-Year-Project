# dashboard_service/gui/main.py
# Author: Andrew Fox

# -----------------------------
# Imports
# -----------------------------
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QGridLayout, QSizePolicy, QDialog,
    QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontDatabase, QFont, QCursor
import pyqtgraph as pg


from collector_service.collector.cpu_collector import CPUCollector


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

        # Graph refresh rate
        self.graph_refresh_rate = 1000 # interval in milliseconds
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_cpu_data)
        self.update_timer.start(self.graph_refresh_rate)

        # Hover timer - updates hover visuals frequently
        self.hover_timer = QTimer()
        self.hover_timer.timeout.connect(self.update_hover)
        self.hover_timer.start(50)

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


        # Alerts dropdown
        self.alerts_button = QPushButton("Alerts")

        # Settings button
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


    def update_cpu_data(self):
        data = CPUCollector.get_cpu_data()

        # Update labels
        cpu_frame = self.section_frames["CPU"][0]
        labels = cpu_frame.labels
        labels["Usage"].setText(f"Usage: {data['cpu_percent_total']:.1f}%")
        labels["Clock"].setText(f"Clock: {data['cpu_freq']['current']:.1f} MHz" if data['cpu_freq'] else "Clock: N/A")
        labels["Temp"].setText("Temp: N/A")

        # Update the rolling buffer for the graph
        cpu_frame.data.append(data['cpu_percent_total'])
        cpu_frame.timestamps.append(datetime.now().strftime("%H:%M:%S"))
        if len(cpu_frame.data) > 50: # Keep only last 50 points
            cpu_frame.data.pop(0)
            cpu_frame.timestamps.pop(0)

        # Update the graph with explicit x coords
        x = list(range(len(cpu_frame.data)))
        cpu_frame.curve.setData(x, cpu_frame.data)
        # keep view stable to 0..49 so mapping from mouse to index is stable
        cpu_frame.plot_widget.plotItem.setXRange(0, 49, padding=0)

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
    # Hover update (runs on timer)
    # -----------------------------
    def update_hover(self):
        # Iterate sections and update hover visuals if mouse over that plot
        for name, (frame, curve, data) in self.section_frames.items():
            plot_widget = frame.plot_widget
            hover_dot = frame.hover_dot
            hover_label = frame.hover_label

            # If plot not visible (e.g., hidden by other panels), skip
            if not plot_widget.isVisible():
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            # If mouse not over this plot, hide visuals
            if not plot_widget.underMouse():
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            # Map cursor to plot coordinates
            view_box = plot_widget.getViewBox()
            mouse_scene = plot_widget.mapToScene(plot_widget.mapFromGlobal(QCursor.pos()))
            try:
                mouse_point = view_box.mapSceneToView(mouse_scene)
            except Exception:
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            x_val = mouse_point.x()

            # Get curve data
            curve_data = curve.getData()
            if not curve_data or len(curve_data[0]) == 0:
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            x_curve, y_curve = curve_data

            # Find nearest index safely
            try:
                # x_curve might be numpy arrays or lists
                nearest_idx = min(range(len(x_curve)), key=lambda i: abs(x_curve[i] - x_val))
            except Exception:
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            y_val = y_curve[nearest_idx]

            # Update the scatter dot
            hover_dot.setData([x_curve[nearest_idx]], [y_val])

            # Prepare label text (value + timestamp if available)
            ts_text = frame.timestamps[nearest_idx] if hasattr(frame, "timestamps") and len(frame.timestamps) > nearest_idx else ""
            label_text = f"{y_val:.1f}%"
            if ts_text:
                label_text += f"  @ {ts_text}"

            # Position the label near the dot (convert to widget coords)
            dot_scene = view_box.mapViewToScene(pg.Point(x_curve[nearest_idx], y_val))
            dot_widget = plot_widget.mapFromScene(dot_scene)

            hover_label.setText(label_text)
            hover_label.adjustSize()
            w, h = hover_label.width(), hover_label.height()

            # Place label to the right unless it would go off the widget, then place left
            x_pos = dot_widget.x() + 10
            if dot_widget.x() + w + 20 > plot_widget.width():
                x_pos = dot_widget.x() - w - 10
            y_pos = dot_widget.y() - h - 5
            hover_label.move(int(x_pos), int(y_pos))
            hover_label.setVisible(True)

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
        plot_widget.setBackground("#2a2a2a")
        plot_widget.setYRange(0, 100)

        # Disable all interactions
        plot_widget.setMouseEnabled(x=False, y=False)
        plot_widget.setMenuEnabled(False)
        plot_widget.setInteractive(False)

        # Hide axis numbers and labels
        plot_widget.getAxis('bottom').setTicks([])
        plot_widget.getAxis('left').setTicks([])
        plot_widget.getAxis('bottom').setStyle(showValues=False)
        plot_widget.getAxis('left').setStyle(showValues=False)
        plot_widget.setLabel('left', '')
        plot_widget.setLabel('bottom', '')

        plot_widget.showGrid(x=False, y=False)

        plot_widget.getAxis('bottom').setPen(None)
        plot_widget.getAxis('left').setPen(None)
        
        plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create explicit X and initial Y to keep mapping stable (0..49)
        initial_x = list(range(50))
        initial_y = [0] * 50
        curve = plot_widget.plot(initial_x, initial_y, pen=pg.mkPen(color='r', width=2))

        # Hover dot (hidden until hover)
        hover_dot = pg.ScatterPlotItem(size=10, brush=pg.mkBrush('r'), pen=pg.mkPen('k'))
        plot_widget.addItem(hover_dot)

        # Hover label as a QLabel overlayed on the plot widget
        hover_label = QLabel("", plot_widget)
        hover_label.setObjectName("hoverLabel")
        hover_label.setVisible(False)
        hover_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Layout balance: keep text narrow, graph wide
        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(plot_widget, stretch=4)

        frame = QFrame()
        frame.setLayout(layout)
        frame.curve = curve
        frame.data = [0] * 50
        frame.timestamps = [datetime.now().strftime("%H:%M:%S")] * 50
        frame.labels = labels
        frame.plot_widget = plot_widget
        frame.hover_dot = hover_dot
        frame.hover_label = hover_label
        frame.setObjectName("sectionFrame")

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
        self.setFixedSize(200, 100)
        self.parent = parent  # reference to main dashboard

        layout = QVBoxLayout()

        # ---------------------------
        # Graph refresh rate
        # ---------------------------
        layout.addWidget(QLabel("Graph Refresh Rate (ms):"))
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(100, 10000)
        self.refresh_spin.setSingleStep(100)
        self.refresh_spin.setValue(parent.graph_refresh_rate)
        layout.addWidget(self.refresh_spin)

        # ---------------------------
        # Buttons
        # ---------------------------
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect buttons
        self.save_button.clicked.connect(self.save_settings)

    def save_settings(self):

        # Update graph refresh rate
        self.parent.graph_refresh_rate = self.refresh_spin.value()
        self.parent.update_timer.setInterval(self.parent.graph_refresh_rate)

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
