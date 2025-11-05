# dashboard_service/gui/live_monitor.py
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
from collector_service.collector.ram_collector import RAMCollector



class LiveSystemMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Sections: CPU, GPU, RAM, Storage
        self.sections = {
            "CPU": {"fields": ["Usage", "Clock", "Temp"]},
            "GPU": {"fields": ["Usage", "Clock", "Temp"]},
            "RAM": {"fields": ["Usage", "Used", "Total"]},
            "Storage": {"fields": ["Usage"]}
        }

        self.section_frames = {}
        grid_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        grid_widget.setLayout(grid_layout)

        # Create each section and place in grid
        names = list(self.sections.keys())
        for name in names:
            frame, curve, data = self.create_section(name, self.sections[name]["fields"])
            self.section_frames[name] = (frame, curve, data)

        grid_layout.addWidget(self.section_frames[names[0]][0], 0, 0)
        grid_layout.addWidget(self.section_frames[names[1]][0], 0, 1)
        grid_layout.addWidget(self.section_frames[names[2]][0], 1, 0)
        grid_layout.addWidget(self.section_frames[names[3]][0], 1, 1)

        layout.addWidget(grid_widget)

        # Timers
        self.graph_refresh_rate = 1000  # milliseconds

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_cpu_data)
        self.update_timer.timeout.connect(self.update_ram_data)
        self.update_timer.start(self.graph_refresh_rate)

        self.hover_timer = QTimer()
        self.hover_timer.timeout.connect(self.update_hover)
        self.hover_timer.start(50)
        
    # -----------------------------
    # CPU Data Update
    # -----------------------------
    def update_cpu_data(self):
        data = CPUCollector.get_cpu_data()

        cpu_frame = self.section_frames["CPU"][0]
        labels = cpu_frame.labels
        labels["Usage"].setText(f"Usage: {data['cpu_percent_total']:.1f}%")
        labels["Clock"].setText(f"Clock: {data['cpu_freq']['current']:.1f} MHz" if data['cpu_freq'] else "Clock: N/A")
        labels["Temp"].setText("Temp: N/A")

        cpu_frame.data.append(data['cpu_percent_total'])
        cpu_frame.timestamps.append(datetime.now().strftime("%H:%M:%S"))
        if len(cpu_frame.data) > 50:
            cpu_frame.data.pop(0)
            cpu_frame.timestamps.pop(0)

        x = list(range(len(cpu_frame.data)))
        cpu_frame.curve.setData(x, cpu_frame.data)
        cpu_frame.plot_widget.plotItem.setXRange(0, 49, padding=0)

    # -----------------------------
    # RAM Data Update
    # -----------------------------
    def update_ram_data(self):
        data = RAMCollector.get_ram_data()

        ram_frame = self.section_frames["RAM"][0]
        labels = ram_frame.labels
        labels["Usage"].setText(f"Usage: {data['ram_usage_percent']:.1f}%")
        labels["Used"].setText(f"Used: {data['used_ram_gb']:.2f} GB")
        labels["Total"].setText(f"Total: {data['total_ram_round_gb']:.2f} GB")

        # Update graph
        ram_frame.data.append(data['ram_usage_percent'])
        ram_frame.timestamps.append(datetime.now().strftime("%H:%M:%S"))
        if len(ram_frame.data) > 50:
            ram_frame.data.pop(0)
            ram_frame.timestamps.pop(0)

        x = list(range(len(ram_frame.data)))
        ram_frame.curve.setData(x, ram_frame.data)
        ram_frame.plot_widget.plotItem.setXRange(0, 49, padding=0)

    # -----------------------------
    # Graph hover update
    # -----------------------------
    def update_hover(self):
        for name, (frame, curve, data) in self.section_frames.items():
            plot_widget = frame.plot_widget
            hover_dot = frame.hover_dot
            hover_label = frame.hover_label

            if not plot_widget.isVisible():
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            if not plot_widget.underMouse():
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            view_box = plot_widget.getViewBox()
            mouse_scene = plot_widget.mapToScene(plot_widget.mapFromGlobal(QCursor.pos()))
            try:
                mouse_point = view_box.mapSceneToView(mouse_scene)
            except Exception:
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            x_val = mouse_point.x()
            curve_data = curve.getData()
            if not curve_data or len(curve_data[0]) == 0:
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            x_curve, y_curve = curve_data
            try:
                nearest_idx = min(range(len(x_curve)), key=lambda i: abs(x_curve[i] - x_val))
            except Exception:
                hover_label.setVisible(False)
                hover_dot.setData([], [])
                continue

            y_val = y_curve[nearest_idx]
            hover_dot.setData([x_curve[nearest_idx]], [y_val])

            ts_text = frame.timestamps[nearest_idx] if hasattr(frame, "timestamps") and len(frame.timestamps) > nearest_idx else ""
            label_text = f"{y_val:.1f}%"
            if ts_text:
                label_text += f"  @ {ts_text}"

            dot_scene = view_box.mapViewToScene(pg.Point(x_curve[nearest_idx], y_val))
            dot_widget = plot_widget.mapFromScene(dot_scene)

            hover_label.setText(label_text)
            hover_label.adjustSize()
            w, h = hover_label.width(), hover_label.height()
            x_pos = dot_widget.x() + 10
            if dot_widget.x() + w + 20 > plot_widget.width():
                x_pos = dot_widget.x() - w - 10
            y_pos = dot_widget.y() - h - 5
            hover_label.move(int(x_pos), int(y_pos))
            hover_label.setVisible(True)

    # -----------------------------
    # Create Section
    # -----------------------------
    def create_section(self, name, fields):
        layout = QHBoxLayout()
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

            label.setAlignment(Qt.AlignmentFlag.AlignRight)
            info_layout.addWidget(label)
            labels[field] = label

        info_layout.addStretch()

        plot_widget = pg.PlotWidget()
        plot_widget.setBackground("#2a2a2a")
        plot_widget.setYRange(0, 100)
        plot_widget.setMouseEnabled(x=False, y=False)
        plot_widget.setMenuEnabled(False)
        plot_widget.setInteractive(False)
        plot_widget.getAxis('bottom').setTicks([])
        plot_widget.getAxis('left').setTicks([])
        plot_widget.showGrid(x=False, y=False)
        plot_widget.getAxis('bottom').setPen(None)
        plot_widget.getAxis('left').setPen(None)
        plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Graph Curve
        initial_x = list(range(50))
        initial_y = [0] * 50
        curve = plot_widget.plot(initial_x, initial_y, pen=pg.mkPen(color='r', width=2))


        hover_dot = pg.ScatterPlotItem(size=10, brush=pg.mkBrush('r'), pen=pg.mkPen('k'))
        plot_widget.addItem(hover_dot)

        hover_label = QLabel("", plot_widget)
        hover_label.setObjectName("hoverLabel")
        hover_label.setVisible(False)
        hover_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

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
    window = LiveSystemMonitor()
    window.show()
    sys.exit(app.exec())
