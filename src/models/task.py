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

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def complete(self):
        self.completed = True
        self.completed_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            'text': self.text,
            'completed': self.completed,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'times_queued': self.times_queued
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
