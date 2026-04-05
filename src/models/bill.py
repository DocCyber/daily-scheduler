"""Bill data model for the bill tracking system."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Bill:
    """Represents a recurring monthly bill."""
    id: str
    name: str
    amount: float
    due_day: int = 1                     # 1-30
    amount_variable: bool = False
    lookahead_days: int = 7
    urgency: str = "gray"                # "red" | "yellow" | "gray"
    category: str = ""
    notes: str = ""
    paid_this_month: bool = False
    last_paid_month: Optional[str] = None  # "YYYY-MM" or None

    def mark_paid(self):
        """Mark this bill as paid for the current month."""
        self.paid_this_month = True
        self.last_paid_month = datetime.now().strftime("%Y-%m")

    def mark_unpaid(self):
        """Undo a paid marking (misclick recovery)."""
        self.paid_this_month = False

    def to_dict(self) -> dict:
        d = {
            'id': self.id,
            'name': self.name,
            'amount': self.amount,
            'due_day': self.due_day,
            'lookahead_days': self.lookahead_days,
            'urgency': self.urgency,
            'paid_this_month': self.paid_this_month,
            'last_paid_month': self.last_paid_month,
        }
        # Only include optional fields if non-default
        if self.amount_variable:
            d['amount_variable'] = True
        if self.category:
            d['category'] = self.category
        if self.notes:
            d['notes'] = self.notes
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'Bill':
        known_fields = {
            'id', 'name', 'amount', 'due_day', 'amount_variable',
            'lookahead_days', 'urgency', 'category', 'notes',
            'paid_this_month', 'last_paid_month'
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
