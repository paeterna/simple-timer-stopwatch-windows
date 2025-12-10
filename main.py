import sys
import threading
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QStackedWidget, QComboBox, QCheckBox, 
                             QDialog, QListWidget, QSpinBox, QFrame, QSizePolicy, QScrollArea)
from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QFont, QAction, QIcon
from logic import TimerEngine
from plyer import notification
try:
    import winsound
except ImportError:
    winsound = None

class ResizableLabel(QLabel):
    def __init__(self, text="", scale_factor=0.4):
        super().__init__(text)
        self.scale_factor = scale_factor
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def resizeEvent(self, event):
        self.adjust_font()
        super().resizeEvent(event)

    def adjust_font(self):
        # Calculate font size based on the smaller dimension to fit well
        size = min(self.width(), self.height())
        font_size = int(size * self.scale_factor)
        if font_size < 10: font_size = 10
        font = self.font()
        font.setPointSize(font_size)
        self.setFont(font)

class HistoryDialog(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Session History")
        self.engine = engine
        self.setFixedSize(300, 400)
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)
        self.populate()

    def populate(self):
        self.list_widget.clear()
        if not self.engine.history:
            self.list_widget.addItem("No completed timers yet")
        else:
            for item in reversed(self.engine.history):
                # Format duration
                mins, secs = divmod(item['duration'], 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    dur_str = f"{hours}:{mins:02}:{secs:02}"
                else:
                    dur_str = f"{mins:02}:{secs:02}"

                ts = item['timestamp'].strftime("%H:%M:%S")
                self.list_widget.addItem(f"#{item['id']} - {dur_str} (at {ts})")

class SettingsDialog(QDialog):
    def __init__(self, engine, main_window, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.engine = engine
        self.main_window = main_window
        self.setFixedSize(300, 250)
        layout = QVBoxLayout()

        # Dark/Light Mode
        self.theme_toggle = QPushButton("Toggle Dark/Light Mode")
        self.theme_toggle.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_toggle)

        # Time Format
        self.format_toggle = QCheckBox("Use 24-hour Format")
        self.format_toggle.setChecked(self.engine.time_format_24h)
        self.format_toggle.toggled.connect(self.set_format)
        layout.addWidget(self.format_toggle)

        # Time Zone
        layout.addWidget(QLabel("Time Zone:"))
        self.use_system_cb = QCheckBox("Use System Time")
        self.use_system_cb.setChecked(self.engine.use_system_time)
        self.use_system_cb.toggled.connect(self.toggle_system_time)
        layout.addWidget(self.use_system_cb)

        self.tz_combo = QComboBox()
        self.tz_combo.addItems(self.engine.available_timezones)
        if self.engine.timezone in self.engine.available_timezones:
            self.tz_combo.setCurrentText(self.engine.timezone)
        self.tz_combo.setEnabled(not self.engine.use_system_time)
        self.tz_combo.currentTextChanged.connect(self.set_timezone)
        layout.addWidget(self.tz_combo)

        self.setLayout(layout)

    def toggle_theme(self):
        self.main_window.toggle_theme()

    def set_format(self, checked):
        self.engine.time_format_24h = checked

    def toggle_system_time(self, checked):
        self.engine.use_system_time = checked
        self.tz_combo.setEnabled(not checked)

    def set_timezone(self, text):
        self.engine.timezone = text

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = TimerEngine()
        self.is_dark = True
        
        self.setWindowTitle("Timer & Clock")
        self.resize(400, 500)
        
        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 1. Top Bar
        top_bar = QHBoxLayout()
        
        self.history_btn = QPushButton("📋")
        self.history_btn.setFixedSize(30, 30)
        self.history_btn.clicked.connect(self.show_history)
        
        self.mode_btn = QPushButton("Timer / Stopwatch")
        self.mode_btn.setCheckable(True) # Unchecked = Timer, Checked = Stopwatch
        self.mode_btn.toggled.connect(self.switch_mode)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.clicked.connect(self.show_settings)

        top_bar.addWidget(self.history_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.mode_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.settings_btn)
        
        self.main_layout.addLayout(top_bar)

        # 2. Middle Area (80% stretch)
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack, stretch=80)

        # --- Timer Page ---
        self.timer_page = QWidget()
        self.timer_layout = QVBoxLayout(self.timer_page)
        
        # Timer Setup View
        self.timer_setup = QWidget()
        setup_layout = QVBoxLayout(self.timer_setup)
        
        # Presets
        presets_layout = QHBoxLayout()
        for label, val in [("5m", 300), ("10m", 600), ("15m", 900), ("30m", 1800), ("1h", 3600)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, v=val: self.set_preset(v))
            presets_layout.addWidget(btn)
        setup_layout.addLayout(presets_layout)
        
        # Numeric Input
        manual_layout = QHBoxLayout()
        self.min_input = QSpinBox()
        self.min_input.setRange(0, 999)
        self.min_input.setSuffix(" m")
        self.sec_input = QSpinBox()
        self.sec_input.setRange(0, 59)
        self.sec_input.setSuffix(" s")
        manual_layout.addWidget(self.min_input)
        manual_layout.addWidget(self.sec_input)
        setup_layout.addLayout(manual_layout)
        
        self.start_timer_btn = QPushButton("Start")
        self.start_timer_btn.setFixedHeight(50)
        self.start_timer_btn.clicked.connect(self.start_timer)
        setup_layout.addWidget(self.start_timer_btn)
        
        self.timer_layout.addWidget(self.timer_setup)

        # Timer Running View
        self.timer_running_view = QWidget()
        self.timer_running_view.setVisible(False)
        running_layout = QVBoxLayout(self.timer_running_view)
        
        self.timer_display = ResizableLabel("00:00", scale_factor=0.3)
        running_layout.addWidget(self.timer_display)
        
        controls_layout = QHBoxLayout()
        self.timer_stop_btn = QPushButton("Pause")
        self.timer_stop_btn.clicked.connect(self.toggle_timer_pause)
        
        self.timer_reset_btn = QPushButton("Reset")
        self.timer_reset_btn.clicked.connect(self.return_to_timer_setup)
        
        controls_layout.addWidget(self.timer_stop_btn)
        controls_layout.addWidget(self.timer_reset_btn)
        running_layout.addLayout(controls_layout)
        
        self.timer_layout.addWidget(self.timer_running_view)
        
        self.stack.addWidget(self.timer_page)

        # --- Stopwatch Page ---
        self.stopwatch_page = QWidget()
        stopwatch_layout = QVBoxLayout(self.stopwatch_page)

        # Main content area with horizontal layout (laps on left, timer on right)
        content_layout = QHBoxLayout()

        # Left side: Laps list (auto-width based on content)
        self.laps_list = QListWidget()
        self.laps_list.setMaximumWidth(150)  # Limit width to fit text
        self.laps_list.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self.laps_list)

        # Right side: Timer display
        self.stopwatch_display = ResizableLabel("00:00.00", scale_factor=0.5)
        content_layout.addWidget(self.stopwatch_display, stretch=1)

        stopwatch_layout.addLayout(content_layout)

        # Controls at bottom
        sw_controls = QHBoxLayout()
        self.sw_lap_reset_btn = QPushButton("Lap")
        self.sw_lap_reset_btn.clicked.connect(self.sw_lap_reset)
        self.sw_start_stop_btn = QPushButton("Start")
        self.sw_start_stop_btn.clicked.connect(self.sw_start_stop)

        sw_controls.addWidget(self.sw_lap_reset_btn)
        sw_controls.addWidget(self.sw_start_stop_btn)
        stopwatch_layout.addLayout(sw_controls)
        
        self.stack.addWidget(self.stopwatch_page)

        # 3. Bottom Area (20% stretch) - Clock
        self.clock_display = ResizableLabel("12:00", scale_factor=0.4)
        self.main_layout.addWidget(self.clock_display, stretch=20)

        # Timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.tick)
        self.update_timer.start(50) # Update every 50ms for smooth UI

        self.apply_theme()
        
        # Fetch timezones in background
        threading.Thread(target=self.engine.fetch_timezones, daemon=True).start()

    def apply_theme(self):
        if self.is_dark:
            self.setStyleSheet("""
                QMainWindow { background-color: #2b2b2b; color: #ffffff; }
                QWidget { color: #ffffff; }
                QPushButton { 
                    background-color: #3b3b3b; 
                    border: 1px solid #555; 
                    border-radius: 5px; 
                    padding: 5px; 
                    color: white;
                }
                QPushButton:hover { background-color: #4b4b4b; }
                QPushButton:checked { background-color: #0078d7; }
                QListWidget { background-color: #333; border: 1px solid #555; }
                QComboBox, QSpinBox { background-color: #333; border: 1px solid #555; color: white; }
                QLabel { color: white; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #f0f0f0; color: #000000; }
                QWidget { color: #000000; }
                QPushButton { 
                    background-color: #e0e0e0; 
                    border: 1px solid #ccc; 
                    border-radius: 5px; 
                    padding: 5px; 
                    color: black;
                }
                QPushButton:hover { background-color: #d0d0d0; }
                QPushButton:checked { background-color: #0078d7; color: white; }
                QListWidget { background-color: white; border: 1px solid #ccc; }
                QComboBox, QSpinBox { background-color: white; border: 1px solid #ccc; color: black; }
                QLabel { color: black; }
            """)

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def show_history(self):
        dlg = HistoryDialog(self.engine, self)
        dlg.exec()

    def show_settings(self):
        dlg = SettingsDialog(self.engine, self, self)
        dlg.exec()

    def switch_mode(self, checked):
        if checked:
            self.stack.setCurrentWidget(self.stopwatch_page)
            self.mode_btn.setText("Stopwatch")
        else:
            self.stack.setCurrentWidget(self.timer_page)
            self.mode_btn.setText("Timer")

    # --- Timer Logic ---
    def set_preset(self, seconds):
        self.min_input.setValue(seconds // 60)
        self.sec_input.setValue(0)

    def start_timer(self):
        minutes = self.min_input.value()
        seconds = self.sec_input.value()
        total = minutes * 60 + seconds
        if total == 0: return

        self.engine.set_timer(total)
        self.engine.start_timer()
        
        self.timer_setup.setVisible(False)
        self.timer_running_view.setVisible(True)
        self.timer_stop_btn.setText("Pause")
        self.timer_stop_btn.setEnabled(True)
        self.timer_display.setText(self.format_time(total))

    def toggle_timer_pause(self):
        if self.engine.timer_running:
            self.engine.pause_timer()
            self.timer_stop_btn.setText("Resume")
        else:
            self.engine.start_timer()
            self.timer_stop_btn.setText("Pause")

    # I need a way to go back to setup.
    # I'll add a 'Reset' button to timer_running_view
    
    # --- Stopwatch Logic ---
    def sw_start_stop(self):
        if self.engine.stopwatch_running:
            self.engine.stop_stopwatch()
            self.sw_start_stop_btn.setText("Start")
            self.sw_lap_reset_btn.setText("Reset")
            self.sw_start_stop_btn.setStyleSheet("background-color: #4CAF50; color: white;") # Greenish
        else:
            self.engine.start_stopwatch()
            self.sw_start_stop_btn.setText("Stop")
            self.sw_lap_reset_btn.setText("Lap")
            self.sw_start_stop_btn.setStyleSheet("background-color: #f44336; color: white;") # Reddish

    def sw_lap_reset(self):
        if self.engine.stopwatch_running:
            # Lap
            t = self.engine.lap_stopwatch()
            self.laps_list.insertItem(0, self.format_time(t, True))
        else:
            # Reset
            self.engine.reset_stopwatch()
            self.laps_list.clear()
            self.stopwatch_display.setText("00:00.00")
            self.sw_start_stop_btn.setText("Start")
            self.sw_lap_reset_btn.setText("Lap")

    def tick(self):
        # Update Clock
        now = self.engine.get_current_time()
        fmt = "%H:%M:%S" if self.engine.time_format_24h else "%I:%M:%S %p"
        self.clock_display.setText(now.strftime(fmt))

        # Update Timer
        if self.stack.currentWidget() == self.timer_page:
            if self.engine.timer_running:
                rem, finished = self.engine.update_timer()
                if finished:
                    self.timer_finished()
                else:
                    self.timer_display.setText(self.format_time(rem))
            elif self.timer_running_view.isVisible():
                 # Update display if paused
                 rem, _ = self.engine.update_timer()
                 self.timer_display.setText(self.format_time(rem))

        # Update Stopwatch
        if self.stack.currentWidget() == self.stopwatch_page:
             t = self.engine.get_stopwatch_time()
             self.stopwatch_display.setText(self.format_time(t, True))

    def timer_finished(self):
        self.timer_display.setText("00:00")
        self.timer_stop_btn.setText("Finished")
        self.timer_stop_btn.setEnabled(False)
        
        # Play sound
        if winsound:
            try:
                winsound.Beep(1000, 1000) # Frequency, Duration
            except:
                pass
        
        # Notification
        try:
            notification.notify(
                title='Timer Finished',
                message='Your timer has ended!',
                app_name='Timer App',
                timeout=10
            )
        except Exception as e:
            print(f"Notification failed: {e}")
            
        # We don't auto-reset. User must press Reset.

    def return_to_timer_setup(self):
        self.timer_running_view.setVisible(False)
        self.timer_setup.setVisible(True)
        self.engine.reset_timer()
        self.timer_stop_btn.setText("Pause") # Default state

    def format_time(self, seconds, show_centiseconds=False):
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        
        if show_centiseconds:
            cs = int((seconds - int(seconds)) * 100)
            if hours > 0:
                return f"{hours:02}:{mins:02}:{secs:02}.{cs:02}"
            return f"{mins:02}:{secs:02}.{cs:02}"
        else:
            if hours > 0:
                return f"{hours:02}:{mins:02}:{secs:02}"
            return f"{mins:02}:{secs:02}"

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
