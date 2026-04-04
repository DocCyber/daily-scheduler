"""Timer manager for handling countdown logic and state transitions."""
from datetime import datetime
from typing import Callable, Optional
from src.models.timer_state import TimerState, SCHEDULE
from src.integrations.voice_monkey import VoiceMonkeyClient
from src.integrations.local_chime import LocalChimeClient


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

        # Initialize announcement clients
        vm_config = self.config.get("voice_monkey", {})
        api_url = vm_config.get("api_url", "")
        timer_config = self.config.get("timer", {})
        enabled = timer_config.get("enable_announcements", True)

        self._vm_client = VoiceMonkeyClient(api_url, enabled)
        self._local_client = LocalChimeClient(enabled)

        # Pick active client based on saved mode
        self.announcement_mode = timer_config.get("announcement_mode", "voice_monkey")
        self.voice_monkey = (
            self._local_client if self.announcement_mode == "local" else self._vm_client
        )

        # Load or create initial timer state
        self.timer_state = self.data_manager.load_timer_state()
        if self.timer_state is None:
            self.timer_state = TimerState.create_initial()
            self._save_state()
        else:
            # If state was saved while running, mark it paused — the tick loop
            # doesn't survive a restart, so start() must be clicked again.
            if self.timer_state.is_running:
                self.timer_state.is_running = False
                self.timer_state.paused_at = datetime.now().isoformat()
                self._save_state()

    def start(self):
        """Start or resume the timer."""
        if not self.timer_state.is_running:
            self._cancel_tick()
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
            return  # Loop ends here; _advance_phase starts a fresh one
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
        # Announcement is handled inside _advance_phase as a transition message
        self._advance_phase()

    def _advance_phase(self):
        """Move to the next phase in the schedule."""
        prev_phase = SCHEDULE[self.timer_state.phase_index]

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

        # Announce transition (what ended → what's starting)
        transition_msg = self._get_transition_message(prev_phase, next_phase)
        self.voice_monkey.announce(transition_msg)

        # Auto-start next phase (no pause between phases)
        self.timer_state.is_running = True
        self.timer_state.started_at = datetime.now().isoformat()

        # Save, notify UI, and start the single fresh tick loop
        self._save_state()
        self.on_state_change(self.timer_state)
        self._tick()

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

    def _get_transition_message(self, prev_phase, next_phase):
        """Generate a single transition announcement: what ended → what's starting."""
        # What ended
        if prev_phase["name"].startswith("Block"):
            ended = f"Block {prev_phase['name'].split()[1]} ended."
        elif prev_phase["name"] == "Planning":
            ended = "Planning ended."
        elif prev_phase["type"] == "break":
            ended = "Break over."
        else:
            ended = f"{prev_phase['name']} ended."

        # What's starting
        if next_phase["name"].startswith("Block"):
            block_num = next_phase["name"].split()[1]
            starting = f"Begin Block {block_num}."
        elif next_phase["name"] == "Planning":
            starting = "Begin planning."
        elif next_phase["type"] == "break":
            duration_min = next_phase["duration"] // 60
            starting = f"Begin {duration_min} minute break."
        else:
            starting = f"Begin {next_phase['name']}."

        return f"{ended} {starting}"

    def _save_state(self):
        """Save timer state to persistence."""
        self.data_manager.save_timer_state(self.timer_state)

    def _cancel_tick(self):
        """Cancel the pending after() callback."""
        if self.after_id is not None:
            self.root_window.after_cancel(self.after_id)
            self.after_id = None

    def set_announcement_mode(self, mode: str):
        """Switch between 'voice_monkey' and 'local' announcement modes and persist."""
        self.announcement_mode = mode
        self.voice_monkey = self._local_client if mode == "local" else self._vm_client

        # Persist to config
        config = self.data_manager.load_config()
        config.setdefault("timer", {})["announcement_mode"] = mode
        self.data_manager.save_config(config)

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
