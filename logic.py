import time
import datetime
import pytz
import requests
from collections import deque

class TimerEngine:
    def __init__(self):
        # Timer State
        self.timer_duration = 0  # in seconds
        self.timer_remaining = 0
        self.timer_running = False
        self.timer_start_time = None
        self.timer_paused_at = 0 # Remaining time when paused

        # Stopwatch State
        self.stopwatch_running = False
        self.stopwatch_start_time = None
        self.stopwatch_elapsed = 0 # Accumulated time before last start
        self.stopwatch_laps = []

        # History
        self.history = [] # List of dicts: {'id': int, 'duration': int, 'timestamp': datetime}
        self.history_counter = 1

        # Settings
        self.timezone = None # None means system time
        self.use_system_time = True
        self.time_format_24h = True
        
        # Load timezones
        self.available_timezones = pytz.all_timezones

    def set_timer(self, seconds):
        self.timer_duration = seconds
        self.timer_remaining = seconds
        self.timer_running = False
        self.timer_paused_at = seconds

    def start_timer(self):
        if not self.timer_running and self.timer_remaining > 0:
            self.timer_start_time = time.time()
            self.timer_running = True

    def pause_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.timer_start_time
            self.timer_remaining -= elapsed
            self.timer_paused_at = self.timer_remaining
            self.timer_running = False

    def reset_timer(self):
        self.timer_running = False
        self.timer_remaining = self.timer_duration
        self.timer_paused_at = self.timer_duration

    def update_timer(self):
        """Updates and returns the remaining time."""
        if self.timer_running:
            elapsed = time.time() - self.timer_start_time
            current_remaining = self.timer_paused_at - elapsed
            if current_remaining <= 0:
                self.timer_remaining = 0
                self.timer_running = False
                self.log_history(self.timer_duration)
                return 0, True # Time, Finished
            self.timer_remaining = current_remaining
            return current_remaining, False
        return self.timer_remaining, False

    def start_stopwatch(self):
        if not self.stopwatch_running:
            self.stopwatch_start_time = time.time()
            self.stopwatch_running = True

    def stop_stopwatch(self):
        if self.stopwatch_running:
            elapsed_since_start = time.time() - self.stopwatch_start_time
            self.stopwatch_elapsed += elapsed_since_start
            self.stopwatch_running = False

    def reset_stopwatch(self):
        self.stopwatch_running = False
        self.stopwatch_elapsed = 0
        self.stopwatch_laps = []

    def lap_stopwatch(self):
        current_time = self.get_stopwatch_time()
        self.stopwatch_laps.append(current_time)
        return current_time

    def get_stopwatch_time(self):
        if self.stopwatch_running:
            return self.stopwatch_elapsed + (time.time() - self.stopwatch_start_time)
        return self.stopwatch_elapsed

    def log_history(self, duration):
        entry = {
            'id': self.history_counter,
            'duration': duration,
            'timestamp': datetime.datetime.now()
        }
        self.history.append(entry)
        self.history_counter += 1

    def get_current_time(self):
        if self.use_system_time or not self.timezone:
            now = datetime.datetime.now()
        else:
            try:
                tz = pytz.timezone(self.timezone)
                now = datetime.datetime.now(tz)
            except pytz.UnknownTimeZoneError:
                now = datetime.datetime.now()
        return now

    def fetch_timezones(self):
        """Tries to fetch timezones from web, falls back to pytz."""
        try:
            response = requests.get("http://worldtimeapi.org/api/timezone", timeout=2)
            if response.status_code == 200:
                self.available_timezones = response.json()
        except Exception:
            pass # Keep default pytz list
