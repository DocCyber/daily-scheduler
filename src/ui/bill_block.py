"""Bill tracking panel widget for the main window."""
import tkinter as tk
from datetime import date


# Urgency color map
URGENCY_COLORS = {
    "red": "#D32F2F",
    "yellow": "#F9A825",
    "gray": "#757575",
}


class BillBlock(tk.LabelFrame):
    """Panel showing bills that are due, overdue, or recently paid."""

    def __init__(self, parent, bill_manager, on_change_callback=None,
                 open_dialog_callback=None):
        super().__init__(
            parent,
            text="Bills",
            font=("Arial", 12, "bold"),
            bg="#1A3A3A",
            fg="white",
            padx=10,
            pady=10,
            relief="ridge",
            borderwidth=2
        )
        self.bill_manager = bill_manager
        self.on_change_callback = on_change_callback
        self.open_dialog_callback = open_dialog_callback
        self._bill_rows = []

        self.create_widgets()
        self.refresh()

    def create_widgets(self):
        """Build the bill panel layout."""
        # Header with counts
        header_frame = tk.Frame(self, bg="#1A3A3A")
        header_frame.pack(fill="x", pady=(0, 5))

        self.header_label = tk.Label(
            header_frame,
            text="Bills",
            font=("Arial", 11, "bold"),
            bg="#1A3A3A",
            fg="white",
            anchor="w"
        )
        self.header_label.pack(side="left")

        self.counts_label = tk.Label(
            header_frame,
            text="",
            font=("Arial", 9),
            bg="#1A3A3A",
            fg="#AAAAAA",
            anchor="e"
        )
        self.counts_label.pack(side="right")

        # Scrollable area
        canvas_frame = tk.Frame(self, bg="#1A3A3A")
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#1A3A3A",
            highlightthickness=0,
            height=200
        )
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#1A3A3A")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._canvas_window, width=e.width)
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bottom button
        btn_frame = tk.Frame(self, bg="#1A3A3A")
        btn_frame.pack(fill="x", pady=(5, 0))

        tk.Button(
            btn_frame,
            text="Manage Bills",
            command=self._on_manage_clicked,
            bg="#2A5A5A",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=3
        ).pack(side="left")

    def _on_manage_clicked(self):
        """Open the bill management dialog."""
        if self.open_dialog_callback:
            self.open_dialog_callback()

    def refresh(self):
        """Rebuild the bill list from current bill_manager state."""
        if self.bill_manager is None:
            return

        today = date.today()

        # Update header counts
        overdue, upcoming = self.bill_manager.get_bill_counts(today)
        paid_count = sum(1 for b in self.bill_manager.bills if b.paid_this_month)
        parts = []
        if overdue > 0:
            parts.append(f"{overdue} overdue")
        if upcoming > 0:
            parts.append(f"{upcoming} upcoming")
        if paid_count > 0:
            parts.append(f"{paid_count} paid")
        self.counts_label.config(text=" | ".join(parts) if parts else "")

        # Clear existing rows
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._bill_rows = []

        # Week 1 cluster
        cluster_bills, cluster_total, cluster_variable = \
            self.bill_manager.get_week1_cluster(today)
        cluster_ids = {b.id for b in cluster_bills}

        if cluster_bills:
            prefix = "~" if cluster_variable else ""
            total_str = f"{prefix}${cluster_total:,.0f}" if cluster_total == int(cluster_total) \
                else f"{prefix}${cluster_total:,.2f}"
            cluster_header = tk.Frame(self.scrollable_frame, bg="#4A1A1A")
            cluster_header.pack(fill="x", pady=(0, 3))
            tk.Label(
                cluster_header,
                text=f"WEEK 1 CLUSTER \u2014 {total_str} total",
                font=("Arial", 10, "bold"),
                bg="#4A1A1A",
                fg="#FF6B6B",
                anchor="w",
                padx=8,
                pady=4
            ).pack(fill="x")

        # Visible bills
        visible = self.bill_manager.get_visible_bills(today)

        if not visible:
            tk.Label(
                self.scrollable_frame,
                text="No bills due right now.",
                font=("Arial", 10, "italic"),
                fg="#AAAAAA",
                bg="#1A3A3A",
                pady=15
            ).pack()
            return

        for bill in visible:
            in_cluster = bill.id in cluster_ids
            self._add_bill_row(bill, today, in_cluster)

    def _add_bill_row(self, bill, today, in_cluster=False):
        """Add a single bill row to the scrollable area."""
        is_overdue = self.bill_manager.is_overdue(bill, today)
        is_paid = bill.paid_this_month

        # Row background
        if is_paid:
            row_bg = "#2A2A2A"  # Dimmed
        elif is_overdue:
            row_bg = "#4A1A1A"  # Red-tinted
        elif in_cluster:
            row_bg = "#3A2A1A"  # Warm tinted for cluster
        else:
            row_bg = "#2A3A3A"  # Default teal-dark

        row = tk.Frame(self.scrollable_frame, bg=row_bg, relief="flat", borderwidth=0)
        row.pack(fill="x", pady=1, padx=2)

        # Urgency indicator (colored bar on left)
        urgency_color = URGENCY_COLORS.get(bill.urgency, URGENCY_COLORS["gray"])
        indicator = tk.Frame(row, bg=urgency_color, width=4)
        indicator.pack(side="left", fill="y", padx=(0, 6))
        indicator.pack_propagate(False)

        # Bill name
        name_fg = "#777777" if is_paid else "white"
        name_font = ("Arial", 10, "overstrike") if is_paid else ("Arial", 10)
        tk.Label(
            row,
            text=bill.name,
            font=name_font,
            bg=row_bg,
            fg=name_fg,
            anchor="w",
            width=22
        ).pack(side="left", padx=(2, 8), pady=4)

        # Amount
        amount_str = self.bill_manager.format_amount(bill)
        amount_fg = "#777777" if is_paid else "#CCCCCC"
        tk.Label(
            row,
            text=amount_str,
            font=("Arial", 10),
            bg=row_bg,
            fg=amount_fg,
            anchor="e",
            width=8
        ).pack(side="left", padx=(0, 8), pady=4)

        # Due status
        status_str = self.bill_manager.format_due_status(bill, today)
        if status_str == "OVERDUE":
            status_fg = "#FF4444"
            status_font = ("Arial", 9, "bold")
        elif status_str == "PAID":
            status_fg = "#4CAF50"
            status_font = ("Arial", 9, "bold")
        else:
            status_fg = "#AAAAAA"
            status_font = ("Arial", 9)

        tk.Label(
            row,
            text=status_str,
            font=status_font,
            bg=row_bg,
            fg=status_fg,
            anchor="w",
            width=16
        ).pack(side="left", padx=(0, 8), pady=4)

        # Notes indicator (small "i" if bill has notes)
        if bill.notes:
            tk.Label(
                row,
                text="i",
                font=("Arial", 8, "italic"),
                bg=row_bg,
                fg="#5A8A8A",
                width=2
            ).pack(side="left", padx=(0, 4), pady=4)

        # Paid checkbox
        paid_var = tk.IntVar(value=1 if is_paid else 0)
        cb = tk.Checkbutton(
            row,
            variable=paid_var,
            command=lambda b=bill, v=paid_var: self._on_paid_toggled(b, v),
            bg=row_bg,
            selectcolor="#2C2C2C",
            activebackground=row_bg,
        )
        cb.pack(side="right", padx=(0, 6), pady=4)

        self._bill_rows.append(row)

    def _on_paid_toggled(self, bill, paid_var):
        """Handle paid checkbox toggle."""
        if paid_var.get():
            self.bill_manager.mark_paid(bill.id)
        else:
            self.bill_manager.mark_unpaid(bill.id)

        # Refresh to re-sort and update visuals
        self.refresh()

        if self.on_change_callback:
            self.on_change_callback()
