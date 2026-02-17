"""Timer manager for handling countdown logic and state transitions."""
from datetime import datetime
from typing import Callable, Optional
from src.models.timer_state import TimerState, SCHEDULE
from src.integrations.voice_monkey import VoiceMonkeyClient


class TimerManager:
    """Manages timer countdown, auto-advance, and announcements."""

    def __init__(
        self,
        data_manager,
        root_window,
        on_state_change_callback: Callable[[TimerState], None]
    ):
        """
        Initialize timer manager.

        Args:
            data_manager: DataManager instance for persistence
            root_window: Tkinter root window for after() scheduling
            on_state_change_callback: Function to call when timer state changes
        """
        self.data_manager = data_manager
        self.root_window = root_window
        self.on_state_change = on_state_change_callback
        self.after_id = None

        # Load configuration
        self.config = self.data_manager.load_config()

        # Initialize Voice Monkey client
        vm_config = self.config.get("voice_monkey", {})
        api_url = vm_config.get("api_url", "")
        timer_config = self.config.get("timer", {})
        enabled = timer_config.get("enable_announcements", True)

        self.voice_monkey = VoiceMonkeyClient(api_url, enabled)

        # Load or create initial timer state
        self.timer_state = self.data_manager.load_timer_state()
        if self.timer_state is None:
            self.timer_state = TimerState.create_initial()
            self._save_state()

    def start(self):
        """Start or resume the timer."""
        if not self.timer_state.is_running:
            self.timer_state.is_running = True
            self.timer_state.started_at = datetime.now().isoformat()
            self.timer_state.paused_at = None

            # Announce what phase is starting
            current_phase = SCHEDULE[self.timer_state.phase_index]
            if current_phase["name"] == "Planning":
                self.voice_monkey.announce("Starting planning phase. 20 minutes to organize your day.")
            elif current_phase["name"].startswith("Block"):
                block_num = current_phase["name"].split()[1]
                self.voice_monkey.announce(f"Starting Block {block_num}. Time to focus.")
            elif current_phase["type"] == "break":
                duration_min = current_phase["duration"] // 60
                self.voice_monkey.announce(f"Starting {duration_min} minute break.")

            self._save_state()
            self._tick()

    def pause(self):
        """Pause the timer."""
        if self.timer_state.is_running:
            self.timer_state.is_running = False
            self.timer_state.paused_at = datetime.now().isoformat()
            self._cancel_tick()
            self._save_state()

    def skip_to_next(self):
        """Skip to the next phase immediately."""
        self._cancel_tick()
        self._advance_phase()

    def reset(self):
        """Reset timer to Planning phase."""
        self._cancel_tick()
        self.timer_state = TimerState.create_initial()
        self._save_state()
        self.on_state_change(self.timer_state)

    def end_day(self):
        """
        End the day early - stop timer and prevent further announcements.
        This prevents speakers from continuing to announce when user leaves.
        """
        self._cancel_tick()
        self.timer_state.is_running = False
        self.timer_state.paused_at = datetime.now().isoformat()
        self._save_state()
        self.on_state_change(self.timer_state)
        print("[Timer] Day ended early by user")

    def _tick(self):
        """Called every second to update timer."""
        if not self.timer_state.is_running:
            return

        # Decrement time
        self.timer_state.time_remaining_seconds -= 1

        # Check if phase is complete
        if self.timer_state.time_remaining_seconds <= 0:
            self._phase_complete()
        else:
            # Check for milestone announcements (5 min, 2 min warnings)
            self._check_milestone_warnings()

        # Save state and notify UI
        self._save_state()
        self.on_state_change(self.timer_state)

        # Schedule next tick
        self.after_id = self.root_window.after(1000, self._tick)

    def _phase_complete(self):
        """Handle phase completion and advance to next phase."""
        current_phase = SCHEDULE[self.timer_state.phase_index]

        # Announce completion
        completion_msg = self._get_completion_message(current_phase)
        self.voice_monkey.announce(completion_msg)

        # Advance to next phase
        self._advance_phase()

    def _advance_phase(self):
        """Move to the next phase in the schedule."""
        # Check if we're at the end of the schedule
        if self.timer_state.phase_index >= len(SCHEDULE) - 1:
            # End of day
            self._end_of_day()
            return

        # Move to next phase
        self.timer_state.phase_index += 1
        next_phase = SCHEDULE[self.timer_state.phase_index]
        self.timer_state.current_phase = next_phase["name"]
        self.timer_state.phase_type = next_phase["type"]
        self.timer_state.time_remaining_seconds = next_phase["duration"]

        # Announce next phase starting
        start_msg = self._get_start_message(next_phase)
        self.voice_monkey.announce(start_msg)

        # Auto-start next phase (no pause between phases)
        self.timer_state.is_running = True
        self.timer_state.started_at = datetime.now().isoformat()

        # Save and continue ticking
        self._save_state()
        self.on_state_change(self.timer_state)

    def _end_of_day(self):
        """Handle end of day (after Block 8)."""
        self.timer_state.is_running = False
        self.timer_state.paused_at = datetime.now().isoformat()
        self._cancel_tick()

        # Final announcement
        self.voice_monkey.announce("Block 8 complete. Your work day is finished!")

        self._save_state()
        self.on_state_change(self.timer_state)
        print("[Timer] Day complete!")

    def _check_milestone_warnings(self):
        """Check if we should announce milestone warnings (5 min, 2 min)."""
        timer_config = self.config.get("timer", {})
        warning_minutes = timer_config.get("warning_at_minutes", [5, 2])

        seconds_remaining = self.timer_state.time_remaining_seconds

        for warning_min in warning_minutes:
            # Check if we're exactly at the warning point
            if seconds_remaining == warning_min * 60:
                if self.timer_state.phase_type == "work":
                    msg = f"{warning_min} minutes remaining in {self.timer_state.current_phase}"
                    self.voice_monkey.announce(msg)
                elif self.timer_state.phase_type == "break":
                    msg = f"Break ending in {warning_min} minutes"
                    self.voice_monkey.announce(msg)

    def _get_completion_message(self, phase):
        """Generate completion announcement message."""
        if phase["name"] == "Planning":
            return "Planning complete. Starting 15 minute break."
        elif phase["name"].startswith("Block"):
            block_num = phase["name"].split()[1]
            if block_num == "5":
                return "Block 5 complete. Starting 30 minute lunch break."
            else:
                return f"Block {block_num} complete. Starting break."
        elif phase["type"] == "break":
            # Determine which block is next
            next_index = self.timer_state.phase_index + 1
            if next_index < len(SCHEDULE):
                next_phase = SCHEDULE[next_index]
                if next_phase["name"].startswith("Block"):
                    block_num = next_phase["name"].split()[1]
                    return f"Break is over. Starting Block {block_num}. Time to focus."
        return "Phase complete."

    def _get_start_message(self, phase):
        """Generate start announcement message."""
        # We announce completion + next phase start together in _get_completion_message
        # This method is mainly for manual skip operations
        if phase["name"].startswith("Block"):
            block_num = phase["name"].split()[1]
            return f"Starting Block {block_num}. Time to focus."
        elif phase["name"] == "Planning":
            return "Starting planning phase."
        elif phase["type"] == "break":
            duration_min = phase["duration"] // 60
            return f"Starting {duration_min} minute break."
        return f"Starting {phase['name']}."

    def _save_state(self):
        """Save timer state to persistence."""
        self.data_manager.save_timer_state(self.timer_state)

    def _cancel_tick(self):
        """Cancel the pending after() callback."""
        if self.after_id is not None:
            self.root_window.after_cancel(self.after_id)
            self.after_id = None

    def validate_config(self) -> bool:
        """
        Validate that Voice Monkey is configured.

        Returns:
            True if configuration is valid, False otherwise
        """
        vm_config = self.config.get("voice_monkey", {})
        api_url = vm_config.get("api_url", "")

        if not api_url or "voicemonkey.io" not in api_url:
            return False

        return True
