# Timer & Clock App

A modern, minimalistic Timer and Clock application for Windows (cross-platform compatible).

## Features

*   **Dual Mode:** Switch between Countdown Timer and Stopwatch.
*   **Minimalistic Design:** Big numbers that resize with the window.
*   **Layout:** 80% Timer/Stopwatch, 20% Real-time Clock.
*   **Timer:**
    *   Quick presets (5m, 10m, 15m, 30m, 1h).
    *   Manual numeric input.
    *   Pause/Resume and Reset functionality.
    *   Audio and System Notifications upon completion.
*   **Stopwatch:**
    *   Start/Stop.
    *   Lap/Reset functionality.
*   **Settings:**
    *   Dark/Light mode toggle.
    *   12h/24h time format.
    *   Time Zone selection (or System Time).
*   **History:** Logs completed timers for the current session.

## Requirements

*   Python 3.x
*   PyQt6
*   pytz
*   requests
*   plyer

## Installation

```bash
pip install PyQt6 pytz requests plyer
```

## Running the App

```bash
python main.py
```
