"""Timer bar UI widget with countdown display and controls."""
import tkinter as tk
from tkinter import ttk
from src.models.timer_state import SCHEDULE


class TimerBar(tk.Frame):
    """Timer display and control widget shown at top of main window."""

    def __init__(self, parent, timer_manager):
        """
        Initialize timer bar.

        Args:
            parent: Parent widget
            timer_manager: TimerManager instance
        """
        super().__init__(parent, bg="#4CAF50", height=80)
        self.timer_manager = timer_manager

        # Color scheme
        self.colors = {
            "work": "#4CAF50",      # Green
            "break": "#2196F3",     # Blue
            "paused": "#FF9800",    # Orange
            "stopped": "#3A3A3A"    # Charcoal
        }

        self.create_widgets()

    def create_widgets(self):
        """Create timer display and control buttons."""
        # Phase label (e.g., "Planning", "Block 1", "Break")
        self.phase_label = tk.Label(
            self,
            text="Planning",
            font=("Arial", 16, "bold"),
            bg=self.colors["work"],
            fg="white"
        )
        self.phase_label.pack(side="left", padx=20)

        # Countdown display (MM:SS)
        self.time_label = tk.Label(
            self,
            text="20:00",
            font=("Arial", 32, "bold"),
            bg=self.colors["work"],
            fg="white"
        )
        self.time_label.pack(side="left", padx=10)

        # Progress bar
        self.progress = ttk.Progressbar(
            self,
            orient="horizontal",
            length=200,
            mode="determinate"
        )
        self.progress.pack(side="left", padx=20)

        # Control buttons frame
        controls_frame = tk.Frame(self, bg=self.colors["work"])
        controls_frame.pack(side="left", padx=20)

        # Start/Resume button
        self.start_btn = tk.Button(
            controls_frame,
            text="▶ Start",
            command=self.timer_manager.start,
            width=10,
            font=("Arial", 10, "bold"),
            bg="white",
            fg=self.colors["work"]
        )
        self.start_btn.grid(row=0, column=0, padx=5, pady=5)

        # Pause button
        self.pause_btn = tk.Button(
            controls_frame,
            text="⏸ Pause",
            command=self.timer_manager.pause,
            width=10,
            font=("Arial", 10),
            bg="white",
            fg=self.colors["paused"]
        )
        self.pause_btn.grid(row=0, column=1, padx=5, pady=5)

        # Skip button
        self.skip_btn = tk.Button(
            controls_frame,
            text="⏭ Skip",
            command=self.timer_manager.skip_to_next,
            width=10,
            font=("Arial", 10),
            bg="white",
            fg="#3A3A3A"
        )
        self.skip_btn.grid(row=0, column=2, padx=5, pady=5)

        # Reset button
        self.reset_btn = tk.Button(
            controls_frame,
            text="↺ Reset",
            command=self.timer_manager.reset,
            width=10,
            font=("Arial", 10),
            bg="white",
            fg="#3A3A3A"
        )
        self.reset_btn.grid(row=1, column=0, padx=5, pady=5)

        # End Day button
        self.end_day_btn = tk.Button(
            controls_frame,
            text="■ End Day",
            command=self.timer_manager.end_day,
            width=10,
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#D32F2F"  # Red
        )
        self.end_day_btn.grid(row=1, column=1, padx=5, pady=5)

    def update_display(self, timer_state):
        """
        Update timer display based on current state.

        Args:
            timer_state: TimerState instance
        """
        # Update time display
        self.time_label.config(text=timer_state.format_time_remaining())

        # Update phase label
        self.phase_label.config(text=timer_state.current_phase)

        # Update background color based on phase type and running state
        if not timer_state.is_running:
            bg_color = self.colors["paused"]
        elif timer_state.phase_type == "work":
            bg_color = self.colors["work"]
        elif timer_state.phase_type == "break":
            bg_color = self.colors["break"]
        else:
            bg_color = self.colors["stopped"]

        self.config(bg=bg_color)
        self.phase_label.config(bg=bg_color)
        self.time_label.config(bg=bg_color)
        controls_frame = self.start_btn.master
        controls_frame.config(bg=bg_color)

        # Update progress bar
        self._update_progress_bar(timer_state)

        # Update button states
        if timer_state.is_running:
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")

    def _update_progress_bar(self, timer_state):
        """Update progress bar based on elapsed time."""
        phase_index = timer_state.phase_index
        if phase_index < len(SCHEDULE):
            total_duration = SCHEDULE[phase_index]["duration"]
            elapsed = total_duration - timer_state.time_remaining_seconds
            progress_percent = (elapsed / total_duration) * 100
            self.progress["value"] = progress_percent
        else:
            self.progress["value"] = 100
