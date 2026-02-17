"""Timer state model and schedule definition for the daily scheduler."""
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime


# Schedule definition: 8-hour workday with planning block
SCHEDULE = [
    {"name": "Planning", "duration": 1200, "type": "work"},     # 20 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 1", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 2", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 3", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 4", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 5", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 1800, "type": "break"},       # 30 min (lunch)
    {"name": "Block 6", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 7", "duration": 2700, "type": "work"},      # 45 min
    {"name": "Break", "duration": 900, "type": "break"},        # 15 min
    {"name": "Block 8", "duration": 2700, "type": "work"},      # 45 min
]


@dataclass
class TimerState:
    """Represents the current state of the timer system."""
    current_phase: str           # "Planning", "Block 1", "Break", etc.
    phase_type: str              # "work" or "break"
    phase_index: int             # 0-16 (sequential position in schedule)
    time_remaining_seconds: int  # Countdown value
    is_running: bool             # Play/pause state
    started_at: Optional[str] = None    # ISO timestamp
    paused_at: Optional[str] = None     # ISO timestamp

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Create TimerState from dictionary."""
        return cls(**data)

    @classmethod
    def create_initial(cls):
        """Create initial timer state (Planning phase, not started)."""
        return cls(
            current_phase="Planning",
            phase_type="work",
            phase_index=0,
            time_remaining_seconds=1200,  # 20 minutes
            is_running=False,
            started_at=None,
            paused_at=None
        )

    def format_time_remaining(self):
        """Format time remaining as MM:SS."""
        minutes = self.time_remaining_seconds // 60
        seconds = self.time_remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
