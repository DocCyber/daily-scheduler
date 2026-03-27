from dataclasses import dataclass, field
from typing import List


@dataclass
class RecurringTask:
    text: str
    target_blocks: List[int] = field(default_factory=list)  # 0-indexed block indices (0-7)
    schedule_type: str = "daily"          # "daily" | "day_of_week" | "day_of_month"
    days_of_week: List[int] = field(default_factory=list)   # 0=Mon … 6=Sun
    days_of_month: List[int] = field(default_factory=list)  # 1-31
    last_applied_date: str = ""           # ISO date string of last application (YYYY-MM-DD)

    def to_dict(self):
        return {
            'text': self.text,
            'target_blocks': self.target_blocks,
            'schedule_type': self.schedule_type,
            'days_of_week': self.days_of_week,
            'days_of_month': self.days_of_month,
            'last_applied_date': self.last_applied_date,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            text=data['text'],
            target_blocks=data.get('target_blocks', []),
            schedule_type=data.get('schedule_type', 'daily'),
            days_of_week=data.get('days_of_week', []),
            days_of_month=data.get('days_of_month', []),
            last_applied_date=data.get('last_applied_date', ''),
        )
