import tkinter as tk
from tkinter import ttk

class TaskItem(tk.Frame):
    """Single task row with checkbox, text entry, and delete button"""

    def __init__(self, parent, task, on_change_callback=None, on_delete_callback=None, on_enter_callback=None):
        super().__init__(parent)
        self.task = task
        self.on_change_callback = on_change_callback
        self.on_delete_callback = on_delete_callback
        self.on_enter_callback = on_enter_callback

        # Checkbox variable
        self.completed_var = tk.IntVar(value=1 if task.completed else 0)

        # Create widgets
        self.checkbox = tk.Checkbutton(
            self,
            variable=self.completed_var,
            command=self.on_checkbox_changed
        )
        self.checkbox.grid(row=0, column=0, padx=(0, 5))

        # Task text entry
        self.text_entry = tk.Entry(self, width=24)
        self.text_entry.insert(0, task.text)
        self.text_entry.bind('<FocusOut>', self.on_text_changed)
        self.text_entry.bind('<Return>', self.on_enter_pressed)
        self.text_entry.grid(row=0, column=1, sticky="ew", padx=5)

        # Delete button
        self.delete_btn = tk.Button(
            self,
            text="×",
            command=self.on_delete,
            width=2,
            fg="red"
        )
        self.delete_btn.grid(row=0, column=2, padx=(5, 0))

        # Make text entry expand
        self.grid_columnconfigure(1, weight=1)

        # Apply strikethrough if completed
        self.update_appearance()

    def on_checkbox_changed(self):
        """Handle checkbox state change"""
        self.task.completed = bool(self.completed_var.get())
        if self.task.completed:
            self.task.complete()
        self.update_appearance()

        if self.on_change_callback:
            self.on_change_callback()

    def on_text_changed(self, event=None):
        """Handle text entry change"""
        new_text = self.text_entry.get().strip()
        if new_text and new_text != self.task.text:
            self.task.text = new_text
            if self.on_change_callback:
                self.on_change_callback()

    def on_enter_pressed(self, event=None):
        """Handle Enter key - save and move to next field"""
        # Save the current text
        self.on_text_changed(event)

        # Trigger auto-save through callback
        if self.on_change_callback:
            self.on_change_callback()

        # Move to next field if callback provided
        if self.on_enter_callback:
            self.on_enter_callback(self)

    def on_delete(self):
        """Handle delete button click"""
        if self.on_delete_callback:
            self.on_delete_callback(self)

    def update_appearance(self):
        """Update visual appearance based on completion status"""
        if self.task.completed:
            self.text_entry.config(fg="gray")
        else:
            self.text_entry.config(fg="black")

    def get_task(self):
        """Return the task object with current values"""
        self.task.text = self.text_entry.get().strip()
        self.task.completed = bool(self.completed_var.get())
        return self.task
