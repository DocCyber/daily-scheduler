import tkinter as tk
from tkinter import messagebox
from ..models.recurring_task import RecurringTask

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class RecurringDialog(tk.Toplevel):
    """Dialog for managing recurring/persistent tasks"""

    def __init__(self, parent, recurring_data, on_save_callback):
        super().__init__(parent)
        self.title("Manage Recurring Tasks")
        self.geometry("520x420")
        self.configure(bg="#2C2C2C")
        self.recurring_data = list(recurring_data)  # work on a copy
        self.on_save_callback = on_save_callback

        self.create_widgets()
        self.populate_list()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

    def create_widgets(self):
        """Build the dialog UI"""
        # Header
        header = tk.Label(
            self, text="Recurring Tasks",
            font=("Arial", 14, "bold"), bg="#2C2C2C", fg="white"
        )
        header.pack(pady=(10, 5))

        info = tk.Label(
            self, text="These tasks auto-populate into their target blocks on each new day.",
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

        self._canvas_window = canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bottom buttons
        btn_frame = tk.Frame(self, bg="#2C2C2C")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            btn_frame, text="+ Add Recurring Task",
            command=self.show_add_form,
            bg="#4A5A4A", fg="white", font=("Arial", 10, "bold"),
            padx=15, pady=5
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_frame, text="Save & Close",
            command=self.save_and_close,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
            padx=15, pady=5
        ).pack(side=tk.RIGHT)

    def populate_list(self):
        """Render all recurring tasks"""
        for widget in self.list_inner.winfo_children():
            widget.destroy()

        if not self.recurring_data:
            tk.Label(
                self.list_inner, text="No recurring tasks yet.",
                font=("Arial", 10, "italic"), fg="#AAAAAA", bg="#2C2C2C"
            ).pack(pady=20)
            return

        for rt in self.recurring_data:
            self._add_list_row(rt)

    def _schedule_summary(self, rt):
        """Return a short human-readable schedule string."""
        if rt.schedule_type == "day_of_week":
            if rt.days_of_week:
                return ", ".join(_DAY_NAMES[d] for d in sorted(rt.days_of_week))
            return "No days"
        elif rt.schedule_type == "day_of_month":
            if rt.days_of_month:
                return "Day " + ", ".join(str(d) for d in sorted(rt.days_of_month))
            return "No days"
        return "Every day"

    def _add_list_row(self, rt):
        """Add a single recurring task row"""
        row = tk.Frame(self.list_inner, bg="#3A3A3A", relief="ridge", borderwidth=1)
        row.pack(fill="x", pady=2)

        # Task text
        block_names = ", ".join(str(b + 1) for b in sorted(rt.target_blocks))
        tk.Label(
            row, text=rt.text,
            font=("Arial", 10), anchor="w",
            bg="#3A3A3A", fg="white", width=22
        ).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        # Schedule summary
        tk.Label(
            row, text=self._schedule_summary(rt),
            font=("Arial", 9, "italic"), fg="#AAAAAA", bg="#3A3A3A", width=14
        ).grid(row=0, column=1, padx=4, pady=6)

        # Target blocks
        tk.Label(
            row, text=f"Blk: {block_names}",
            font=("Arial", 9, "italic"), fg="#AAAAAA", bg="#3A3A3A"
        ).grid(row=0, column=2, padx=8, pady=6)

        # Edit button
        tk.Button(
            row, text="Edit",
            command=lambda r=rt: self.show_edit_form(r),
            font=("Arial", 8), bg="#1A3A5C", fg="white", width=5
        ).grid(row=0, column=3, padx=4, pady=4)

        # Delete button
        tk.Button(
            row, text="×",
            command=lambda r=rt: self.delete_recurring(r),
            font=("Arial", 10), fg="#FF6B6B", bg="#3A3A3A", width=3
        ).grid(row=0, column=4, padx=4, pady=4)

        row.grid_columnconfigure(0, weight=1)

    def show_add_form(self):
        """Show inline form to add a new recurring task"""
        self._show_form(None)

    def show_edit_form(self, rt):
        """Show inline form to edit an existing recurring task"""
        self._show_form(rt)

    def _show_form(self, existing_rt):
        """Show add/edit form as a popup"""
        form = tk.Toplevel(self)
        form.title("Edit Recurring Task" if existing_rt else "Add Recurring Task")
        form.geometry("420x460")
        form.configure(bg="#2C2C2C")
        form.transient(self)
        form.grab_set()

        # Task text
        tk.Label(form, text="Task text:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15, 5))
        text_entry = tk.Entry(form, width=44, font=("Arial", 10))
        text_entry.pack(padx=15)
        if existing_rt:
            text_entry.insert(0, existing_rt.text)

        # ── Schedule type ──────────────────────────────────────────────────
        tk.Label(form, text="Schedule:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(anchor="w", padx=15, pady=(12, 4))

        sched_var = tk.StringVar(value=existing_rt.schedule_type if existing_rt else "daily")

        sched_frame = tk.Frame(form, bg="#2C2C2C")
        sched_frame.pack(anchor="w", padx=15)

        # Container that swaps between day-of-week and day-of-month pickers
        picker_frame = tk.Frame(form, bg="#2C2C2C")
        picker_frame.pack(anchor="w", padx=15, fill="x")

        # Day-of-week checkboxes (Mon–Sun)
        dow_frame = tk.Frame(picker_frame, bg="#2C2C2C")
        dow_vars = []
        for i, name in enumerate(_DAY_NAMES):
            v = tk.IntVar(value=1 if existing_rt and i in existing_rt.days_of_week else 0)
            dow_vars.append(v)
            tk.Checkbutton(
                dow_frame, text=name, variable=v,
                bg="#2C2C2C", fg="white", selectcolor="#3A3A3A",
                activebackground="#2C2C2C", font=("Arial", 9)
            ).grid(row=0, column=i, sticky="w", padx=3)

        # Day-of-month grid (1–31)
        dom_frame = tk.Frame(picker_frame, bg="#2C2C2C")
        dom_vars = []
        for day in range(1, 32):
            v = tk.IntVar(value=1 if existing_rt and day in existing_rt.days_of_month else 0)
            dom_vars.append(v)
            tk.Checkbutton(
                dom_frame, text=str(day), variable=v,
                bg="#2C2C2C", fg="white", selectcolor="#3A3A3A",
                activebackground="#2C2C2C", font=("Arial", 8), width=2
            ).grid(row=(day - 1) // 7, column=(day - 1) % 7, sticky="w")

        dom_warning = tk.Label(
            dom_frame,
            text="Days 29-31 are skipped in months that don't have them.",
            font=("Arial", 8, "italic"), fg="#AAAAAA", bg="#2C2C2C"
        )
        dom_warning.grid(row=5, column=0, columnspan=7, sticky="w", pady=(4, 0))

        def refresh_picker(*_):
            dow_frame.pack_forget()
            dom_frame.pack_forget()
            mode = sched_var.get()
            if mode == "day_of_week":
                dow_frame.pack(anchor="w")
            elif mode == "day_of_month":
                dom_frame.pack(anchor="w")

        for val, label in [("daily", "Every day"), ("day_of_week", "Days of week"),
                            ("day_of_month", "Day of month")]:
            tk.Radiobutton(
                sched_frame, text=label, variable=sched_var, value=val,
                command=refresh_picker,
                bg="#2C2C2C", fg="white", selectcolor="#3A3A3A",
                activebackground="#2C2C2C", font=("Arial", 9)
            ).pack(side=tk.LEFT, padx=6)

        refresh_picker()  # Show correct picker for initial state

        # ── Block checkboxes ────────────────────────────────────────────────
        tk.Label(form, text="Target blocks:", bg="#2C2C2C", fg="white",
                 font=("Arial", 10)).pack(anchor="w", padx=15, pady=(12, 4))

        checks_frame = tk.Frame(form, bg="#2C2C2C")
        checks_frame.pack(padx=15, anchor="w")

        block_vars = []
        for i in range(8):
            var = tk.IntVar(value=1 if existing_rt and i in existing_rt.target_blocks else 0)
            block_vars.append(var)
            tk.Checkbutton(
                checks_frame, text=f"Block {i+1}", variable=var,
                bg="#2C2C2C", fg="white", selectcolor="#3A3A3A",
                activebackground="#2C2C2C", font=("Arial", 9)
            ).grid(row=i // 4, column=i % 4, sticky="w", padx=5, pady=2)

        # ── Save / Cancel ───────────────────────────────────────────────────
        btn_frame = tk.Frame(form, bg="#2C2C2C")
        btn_frame.pack(pady=12)

        def save():
            text = text_entry.get().strip()
            if not text:
                messagebox.showwarning("Missing Text", "Please enter task text.", parent=form)
                return
            selected_blocks = [i for i, v in enumerate(block_vars) if v.get()]
            if not selected_blocks:
                messagebox.showwarning("No Blocks", "Please select at least one target block.", parent=form)
                return

            stype = sched_var.get()
            sel_dow = [i for i, v in enumerate(dow_vars) if v.get()]
            sel_dom = [day for day, v in enumerate(dom_vars, start=1) if v.get()]

            if stype == "day_of_week" and not sel_dow:
                messagebox.showwarning("No Days", "Please select at least one day of the week.", parent=form)
                return
            if stype == "day_of_month" and not sel_dom:
                messagebox.showwarning("No Days", "Please select at least one day of the month.", parent=form)
                return

            if existing_rt:
                existing_rt.text = text
                existing_rt.target_blocks = selected_blocks
                existing_rt.schedule_type = stype
                existing_rt.days_of_week = sel_dow
                existing_rt.days_of_month = sel_dom
            else:
                self.recurring_data.append(RecurringTask(
                    text=text,
                    target_blocks=selected_blocks,
                    schedule_type=stype,
                    days_of_week=sel_dow,
                    days_of_month=sel_dom,
                ))

            form.destroy()
            self.populate_list()

        tk.Button(btn_frame, text="Save", command=save,
                  bg="#4CAF50", fg="white", font=("Arial", 10), width=8).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancel", command=form.destroy,
                  font=("Arial", 10), width=8).pack(side=tk.LEFT, padx=10)

    def delete_recurring(self, rt):
        """Delete a recurring task"""
        if messagebox.askyesno("Confirm", f"Delete recurring task '{rt.text}'?", parent=self):
            self.recurring_data.remove(rt)
            self.populate_list()

    def save_and_close(self):
        """Save changes and close dialog"""
        self.on_save_callback(self.recurring_data)
        self.destroy()
