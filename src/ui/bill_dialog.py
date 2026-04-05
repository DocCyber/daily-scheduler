"""Dialog for managing bills (add, edit, delete)."""
import tkinter as tk
from tkinter import messagebox
from ..models.bill import Bill


class BillDialog(tk.Toplevel):
    """Dialog for managing the full bill list."""

    def __init__(self, parent, bill_manager, on_save_callback):
        super().__init__(parent)
        self.title("Manage Bills")
        self.geometry("640x520")
        self.configure(bg="#2C2C2C")
        self.bill_manager = bill_manager
        # Work on a copy so Cancel discards changes
        self._bills_copy = [Bill.from_dict(b.to_dict()) for b in bill_manager.bills]
        self.on_save_callback = on_save_callback

        self.create_widgets()
        self.populate_list()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

    def create_widgets(self):
        """Build the dialog UI."""
        # Header
        header = tk.Label(
            self, text="Manage Bills",
            font=("Arial", 14, "bold"), bg="#2C2C2C", fg="white"
        )
        header.pack(pady=(10, 5))

        info = tk.Label(
            self, text="Add, edit, or remove bills. Changes apply when you click Save & Close.",
            font=("Arial", 9, "italic"), bg="#2C2C2C", fg="#AAAAAA"
        )
        info.pack(pady=(0, 10))

        # Scrollable list area
        list_frame = tk.Frame(self, bg="#2C2C2C")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        canvas = tk.Canvas(list_frame, bg="#2C2C2C", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)

        self.list_inner = tk.Frame(canvas, bg="#2C2C2C")
        self.list_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._canvas_window = canvas.create_window(
            (0, 0), window=self.list_inner, anchor="nw"
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._canvas_window, width=e.width)
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bottom buttons
        btn_frame = tk.Frame(self, bg="#2C2C2C")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            btn_frame, text="+ Add Bill",
            command=self.show_add_form,
            bg="#2A5A5A", fg="white", font=("Arial", 10, "bold"),
            padx=15, pady=5
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_frame, text="Save & Close",
            command=self.save_and_close,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
            padx=15, pady=5
        ).pack(side=tk.RIGHT)

        tk.Button(
            btn_frame, text="Cancel",
            command=self.destroy,
            font=("Arial", 10),
            padx=15, pady=5
        ).pack(side=tk.RIGHT, padx=5)

    def populate_list(self):
        """Render all bills in the list."""
        for widget in self.list_inner.winfo_children():
            widget.destroy()

        if not self._bills_copy:
            tk.Label(
                self.list_inner, text="No bills yet. Click '+ Add Bill' to get started.",
                font=("Arial", 10, "italic"), fg="#AAAAAA", bg="#2C2C2C"
            ).pack(pady=20)
            return

        # Group by urgency for visual clarity
        urgency_order = {"red": 0, "yellow": 1, "gray": 2}
        sorted_bills = sorted(self._bills_copy,
                              key=lambda b: (urgency_order.get(b.urgency, 3), b.due_day))

        current_urgency = None
        urgency_labels = {"red": "RED (Non-negotiable)", "yellow": "YELLOW (Important)",
                          "gray": "GRAY (Can float)"}

        for bill in sorted_bills:
            # Section header when urgency changes
            if bill.urgency != current_urgency:
                current_urgency = bill.urgency
                label_text = urgency_labels.get(current_urgency, current_urgency.upper())
                urgency_colors = {"red": "#D32F2F", "yellow": "#F9A825", "gray": "#757575"}
                tk.Label(
                    self.list_inner,
                    text=label_text,
                    font=("Arial", 9, "bold"),
                    bg="#2C2C2C",
                    fg=urgency_colors.get(current_urgency, "#AAAAAA"),
                    anchor="w"
                ).pack(fill="x", padx=4, pady=(8, 2))

            self._add_list_row(bill)

    def _add_list_row(self, bill):
        """Add a single bill row to the dialog list."""
        row = tk.Frame(self.list_inner, bg="#3A3A3A", relief="ridge", borderwidth=1)
        row.pack(fill="x", pady=1)

        # Name
        tk.Label(
            row, text=bill.name,
            font=("Arial", 10), anchor="w",
            bg="#3A3A3A", fg="white", width=20
        ).grid(row=0, column=0, sticky="w", padx=8, pady=4)

        # Amount
        prefix = "~" if bill.amount_variable else ""
        amount_str = f"{prefix}${bill.amount:,.0f}" if bill.amount == int(bill.amount) \
            else f"{prefix}${bill.amount:,.2f}"
        tk.Label(
            row, text=amount_str,
            font=("Arial", 9), fg="#AAAAAA", bg="#3A3A3A", width=8
        ).grid(row=0, column=1, padx=4, pady=4)

        # Due day
        tk.Label(
            row, text=f"Due {self.bill_manager._ordinal(bill.due_day)}",
            font=("Arial", 9, "italic"), fg="#AAAAAA", bg="#3A3A3A", width=10
        ).grid(row=0, column=2, padx=4, pady=4)

        # Edit button
        tk.Button(
            row, text="Edit",
            command=lambda b=bill: self.show_edit_form(b),
            font=("Arial", 8), bg="#1A3A5C", fg="white", width=5
        ).grid(row=0, column=3, padx=4, pady=3)

        # Delete button
        tk.Button(
            row, text="\u00d7",
            command=lambda b=bill: self.delete_bill(b),
            font=("Arial", 10), fg="#FF6B6B", bg="#3A3A3A", width=3
        ).grid(row=0, column=4, padx=4, pady=3)

        row.grid_columnconfigure(0, weight=1)

    def show_add_form(self):
        """Show form to add a new bill."""
        self._show_form(None)

    def show_edit_form(self, bill):
        """Show form to edit an existing bill."""
        self._show_form(bill)

    def _show_form(self, existing_bill):
        """Show add/edit form as a modal sub-dialog."""
        form = tk.Toplevel(self)
        form.title("Edit Bill" if existing_bill else "Add Bill")
        form.geometry("400x500")
        form.configure(bg="#2C2C2C")
        form.transient(self)
        form.grab_set()

        # Name
        tk.Label(form, text="Bill name:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15, 3))
        name_entry = tk.Entry(form, width=40, font=("Arial", 10))
        name_entry.pack(padx=15)
        if existing_bill:
            name_entry.insert(0, existing_bill.name)

        # Amount row
        amount_frame = tk.Frame(form, bg="#2C2C2C")
        amount_frame.pack(fill="x", padx=15, pady=(10, 0))

        tk.Label(amount_frame, text="Amount ($):", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(side="left")
        amount_entry = tk.Entry(amount_frame, width=10, font=("Arial", 10))
        amount_entry.pack(side="left", padx=(5, 15))
        if existing_bill:
            amount_entry.insert(0, str(existing_bill.amount))

        variable_var = tk.IntVar(value=1 if existing_bill and existing_bill.amount_variable else 0)
        tk.Checkbutton(
            amount_frame, text="Variable amount (~)",
            variable=variable_var,
            bg="#2C2C2C", fg="white", selectcolor="#3A3A3A",
            activebackground="#2C2C2C", font=("Arial", 9)
        ).pack(side="left")

        # Due day
        due_frame = tk.Frame(form, bg="#2C2C2C")
        due_frame.pack(fill="x", padx=15, pady=(10, 0))

        tk.Label(due_frame, text="Due day (1-30):", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(side="left")
        due_spinbox = tk.Spinbox(due_frame, from_=1, to=30, width=5, font=("Arial", 10))
        due_spinbox.pack(side="left", padx=5)
        if existing_bill:
            due_spinbox.delete(0, tk.END)
            due_spinbox.insert(0, str(existing_bill.due_day))

        # Lookahead days
        tk.Label(due_frame, text="Lookahead:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=(15, 0))
        lookahead_spinbox = tk.Spinbox(due_frame, from_=1, to=14, width=4, font=("Arial", 10))
        lookahead_spinbox.pack(side="left", padx=5)
        if existing_bill:
            lookahead_spinbox.delete(0, tk.END)
            lookahead_spinbox.insert(0, str(existing_bill.lookahead_days))
        else:
            lookahead_spinbox.delete(0, tk.END)
            lookahead_spinbox.insert(0, "7")

        # Urgency
        tk.Label(form, text="Urgency:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(anchor="w", padx=15, pady=(10, 3))
        urgency_frame = tk.Frame(form, bg="#2C2C2C")
        urgency_frame.pack(anchor="w", padx=15)

        urgency_var = tk.StringVar(value=existing_bill.urgency if existing_bill else "gray")
        for val, label, color in [("red", "Red (non-negotiable)", "#D32F2F"),
                                  ("yellow", "Yellow (important)", "#F9A825"),
                                  ("gray", "Gray (can float)", "#757575")]:
            tk.Radiobutton(
                urgency_frame, text=label, variable=urgency_var, value=val,
                bg="#2C2C2C", fg=color, selectcolor="#3A3A3A",
                activebackground="#2C2C2C", font=("Arial", 9)
            ).pack(anchor="w")

        # Category
        cat_frame = tk.Frame(form, bg="#2C2C2C")
        cat_frame.pack(fill="x", padx=15, pady=(10, 0))

        tk.Label(cat_frame, text="Category:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(side="left")
        category_entry = tk.Entry(cat_frame, width=20, font=("Arial", 10))
        category_entry.pack(side="left", padx=5)
        if existing_bill and existing_bill.category:
            category_entry.insert(0, existing_bill.category)

        # Notes
        tk.Label(form, text="Notes:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(anchor="w", padx=15, pady=(10, 3))
        notes_entry = tk.Entry(form, width=44, font=("Arial", 10))
        notes_entry.pack(padx=15)
        if existing_bill and existing_bill.notes:
            notes_entry.insert(0, existing_bill.notes)

        # Save / Cancel
        btn_frame = tk.Frame(form, bg="#2C2C2C")
        btn_frame.pack(pady=15)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Missing Name", "Please enter a bill name.",
                                       parent=form)
                return

            try:
                amount = float(amount_entry.get().strip())
            except ValueError:
                messagebox.showwarning("Invalid Amount", "Please enter a valid number.",
                                       parent=form)
                return

            try:
                due_day = int(due_spinbox.get().strip())
                if due_day < 1 or due_day > 30:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid Due Day", "Due day must be 1-30.",
                                       parent=form)
                return

            try:
                lookahead = int(lookahead_spinbox.get().strip())
                if lookahead < 1 or lookahead > 14:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid Lookahead", "Lookahead must be 1-14 days.",
                                       parent=form)
                return

            if existing_bill:
                existing_bill.name = name
                existing_bill.amount = amount
                existing_bill.amount_variable = bool(variable_var.get())
                existing_bill.due_day = due_day
                existing_bill.lookahead_days = lookahead
                existing_bill.urgency = urgency_var.get()
                existing_bill.category = category_entry.get().strip()
                existing_bill.notes = notes_entry.get().strip()
            else:
                new_bill = Bill(
                    id="",  # Will be generated on save
                    name=name,
                    amount=amount,
                    amount_variable=bool(variable_var.get()),
                    due_day=due_day,
                    lookahead_days=lookahead,
                    urgency=urgency_var.get(),
                    category=category_entry.get().strip(),
                    notes=notes_entry.get().strip(),
                )
                # Generate ID from name
                import re
                slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
                existing_ids = {b.id for b in self._bills_copy}
                if slug not in existing_ids:
                    new_bill.id = slug
                else:
                    counter = 2
                    while f"{slug}_{counter}" in existing_ids:
                        counter += 1
                    new_bill.id = f"{slug}_{counter}"
                self._bills_copy.append(new_bill)

            form.destroy()
            self.populate_list()

        tk.Button(btn_frame, text="Save", command=save,
                  bg="#4CAF50", fg="white", font=("Arial", 10),
                  width=8).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancel", command=form.destroy,
                  font=("Arial", 10), width=8).pack(side=tk.LEFT, padx=10)

    def delete_bill(self, bill):
        """Delete a bill from the working copy."""
        if messagebox.askyesno("Confirm",
                               f"Delete bill '{bill.name}'?", parent=self):
            self._bills_copy.remove(bill)
            self.populate_list()

    def save_and_close(self):
        """Commit changes and close."""
        self.on_save_callback(self._bills_copy)
        self.destroy()
