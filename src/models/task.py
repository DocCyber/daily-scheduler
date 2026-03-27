from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Task:
    text: str
    completed: bool = False
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    times_queued: int = 0
    is_recurring: bool = False
    is_high_priority: bool = False
    blocks_escalated: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def complete(self):
        self.completed = True
        self.completed_at = datetime.now().isoformat()

    def to_dict(self):
        d = {
            'text': self.text,
            'completed': self.completed,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'times_queued': self.times_queued,
        }
        if self.is_recurring:
            d['is_recurring'] = True
        if self.is_high_priority:
            d['is_high_priority'] = True
        if self.blocks_escalated:
            d['blocks_escalated'] = self.blocks_escalated
        return d

    @classmethod
    def from_dict(cls, data):
        # Filter to only known fields for backward compatibility
        known_fields = {'text', 'completed', 'created_at', 'completed_at', 'times_queued', 'is_recurring', 'is_high_priority', 'blocks_escalated'}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
