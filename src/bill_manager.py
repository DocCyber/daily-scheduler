"""Bill manager for tracking monthly bills, due dates, and payment status."""
import re
import calendar
from datetime import date, timedelta
from typing import List, Tuple, Optional
from src.models.bill import Bill


class BillManager:
    """Manages bill tracking, due date calculations, and month resets."""

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.bills: List[Bill] = []
        self.last_reset_month: str = ""
        self.load()

    def load(self):
        """Load bills from disk and run month reset if needed."""
        self.bills, self.last_reset_month = self.data_manager.load_bills()
        self.reset_month_if_needed()

    def save(self):
        """Persist bills to disk."""
        self.data_manager.save_bills(self.bills, self.last_reset_month)

    # ── Month reset ─────────────────────────────────────────────────────

    def reset_month_if_needed(self):
        """Clear paid_this_month for all bills if the month has changed.

        Compares last_reset_month against current month. Idempotent — safe
        to call on every load. Handles skipped months (any month mismatch
        triggers reset, regardless of gap).
        """
        current_month = date.today().strftime("%Y-%m")
        if self.last_reset_month and self.last_reset_month == current_month:
            return  # Already reset this month

        if self.last_reset_month:
            print(f"[Bills] Month changed ({self.last_reset_month} → {current_month}), resetting paid status")

        for bill in self.bills:
            bill.paid_this_month = False

        self.last_reset_month = current_month
        self.save()

    # ── Due date calculations ───────────────────────────────────────────

    @staticmethod
    def get_effective_due_day(due_day: int, year: int, month: int) -> int:
        """Clamp due_day to the last day of the given month.

        Bills due on the 30th in February become due on the 28th (or 29th).
        """
        _, last_day = calendar.monthrange(year, month)
        return min(due_day, last_day)

    def is_overdue(self, bill: Bill, today: Optional[date] = None) -> bool:
        """Check if a bill is past its due date and unpaid this month."""
        if today is None:
            today = date.today()
        if bill.paid_this_month:
            return False
        effective_day = self.get_effective_due_day(bill.due_day, today.year, today.month)
        return today.day > effective_day

    def is_due_soon(self, bill: Bill, today: Optional[date] = None) -> bool:
        """Check if a bill is within its lookahead window or overdue.

        Handles lookahead crossing month boundaries (e.g., Dec 27 shows
        a bill due Jan 3 with 7-day lookahead).
        """
        if today is None:
            today = date.today()

        # Already paid this month — not "due soon"
        if bill.paid_this_month:
            return False

        lookahead = timedelta(days=bill.lookahead_days)

        # Check this month's due date
        eff_day = self.get_effective_due_day(bill.due_day, today.year, today.month)
        due_this_month = date(today.year, today.month, eff_day)

        # Overdue (past due, unpaid)
        if today > due_this_month:
            return True

        # Within lookahead for this month
        if due_this_month - today <= lookahead:
            return True

        # Check next month's due date (cross-boundary lookahead)
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        eff_day_next = self.get_effective_due_day(bill.due_day, next_year, next_month)
        due_next_month = date(next_year, next_month, eff_day_next)

        if due_next_month - today <= lookahead:
            return True

        return False

    def get_visible_bills(self, today: Optional[date] = None) -> List[Bill]:
        """Get all bills that should be displayed (due soon, overdue, or paid).

        Returns bills sorted: overdue first, then by due_day ascending,
        paid bills at the bottom.
        """
        if today is None:
            today = date.today()

        visible = []
        for bill in self.bills:
            if bill.paid_this_month or self.is_due_soon(bill, today):
                visible.append(bill)

        # Sort: overdue first, then by due_day, paid at bottom
        def sort_key(b):
            if b.paid_this_month:
                return (2, b.due_day)  # Paid goes last
            elif self.is_overdue(b, today):
                return (0, b.due_day)  # Overdue first
            else:
                return (1, b.due_day)  # Upcoming in middle

        visible.sort(key=sort_key)
        return visible

    def get_week1_cluster(self, today: Optional[date] = None) -> Tuple[List[Bill], float, bool]:
        """Get week-1 cluster info if active.

        The cluster is active when today is between the 25th and the 5th.
        Shows bills with due_day 1-7.

        Returns:
            (cluster_bills, total_amount, has_variable)
            Returns ([], 0.0, False) if cluster is not active.
        """
        if today is None:
            today = date.today()

        # Cluster active on days 25-31 or 1-5
        if not (today.day >= 25 or today.day <= 5):
            return [], 0.0, False

        cluster_bills = [
            b for b in self.bills
            if b.due_day >= 1 and b.due_day <= 7 and not b.paid_this_month
        ]

        if not cluster_bills:
            return [], 0.0, False

        total = sum(b.amount for b in cluster_bills)
        has_variable = any(b.amount_variable for b in cluster_bills)

        # Sort by due_day
        cluster_bills.sort(key=lambda b: b.due_day)

        return cluster_bills, total, has_variable

    def get_bill_counts(self, today: Optional[date] = None) -> Tuple[int, int]:
        """Get counts for the header: (overdue_count, upcoming_count)."""
        if today is None:
            today = date.today()

        overdue = 0
        upcoming = 0
        for bill in self.bills:
            if bill.paid_this_month:
                continue
            if self.is_overdue(bill, today):
                overdue += 1
            elif self.is_due_soon(bill, today):
                upcoming += 1

        return overdue, upcoming

    # ── CRUD ────────────────────────────────────────────────────────────

    def mark_paid(self, bill_id: str):
        """Mark a bill as paid this month."""
        for bill in self.bills:
            if bill.id == bill_id:
                bill.mark_paid()
                self.save()
                return

    def mark_unpaid(self, bill_id: str):
        """Undo a paid marking (misclick recovery)."""
        for bill in self.bills:
            if bill.id == bill_id:
                bill.mark_unpaid()
                self.save()
                return

    def add_bill(self, bill: Bill):
        """Add a new bill. Generates a unique ID if needed."""
        if not bill.id:
            bill.id = self._generate_id(bill.name)
        self.bills.append(bill)
        self.save()

    def remove_bill(self, bill_id: str):
        """Remove a bill by ID."""
        self.bills = [b for b in self.bills if b.id != bill_id]
        self.save()

    def get_bill_by_id(self, bill_id: str) -> Optional[Bill]:
        """Find a bill by its ID."""
        for bill in self.bills:
            if bill.id == bill_id:
                return bill
        return None

    # ── ID generation ───────────────────────────────────────────────────

    def _generate_id(self, name: str) -> str:
        """Generate a unique slug ID from a bill name."""
        slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        existing_ids = {b.id for b in self.bills}

        if slug not in existing_ids:
            return slug

        counter = 2
        while f"{slug}_{counter}" in existing_ids:
            counter += 1
        return f"{slug}_{counter}"

    def format_due_status(self, bill: Bill, today: Optional[date] = None) -> str:
        """Format a human-readable due status string for display."""
        if today is None:
            today = date.today()

        if bill.paid_this_month:
            return "PAID"

        eff_day = self.get_effective_due_day(bill.due_day, today.year, today.month)

        if self.is_overdue(bill, today):
            return f"OVERDUE ({self._ordinal(eff_day)})"

        # Format ordinal suffix
        return f"due {self._ordinal(eff_day)}"

    @staticmethod
    def _ordinal(n: int) -> str:
        """Return number with ordinal suffix (1st, 2nd, 3rd, etc.)."""
        if 11 <= n <= 13:
            return f"{n}th"
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def format_amount(self, bill: Bill) -> str:
        """Format amount for display, with ~ prefix if variable."""
        prefix = "~" if bill.amount_variable else ""
        # Show as integer if no cents, otherwise 2 decimal places
        if bill.amount == int(bill.amount):
            return f"{prefix}${int(bill.amount)}"
        return f"{prefix}${bill.amount:.2f}"
