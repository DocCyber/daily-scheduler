import tkinter as tk
from tkinter import ttk
from .task_item import TaskItem
from ..models.task import Task

class TaskBlock(tk.LabelFrame):
    """Task block widget with title, block complete checkbox, and task list"""

    def __init__(self, parent, block_data, on_change_callback=None):
        super().__init__(parent, text=f"{block_data.name} - 45 minutes",
                        font=("Arial", 10, "bold"), padx=10, pady=10)
        self.block_data = block_data
        self.on_change_callback = on_change_callback
        self.task_items = []

        # Create scrollable frame for tasks
        self.create_widgets()
        self.populate_tasks()

    def create_widgets(self):
        """Create the block UI structure"""
        # Block complete checkbox at top
        self.block_complete_var = tk.IntVar(value=1 if self.block_data.block_completed else 0)
        self.block_complete_check = tk.Checkbutton(
            self,
            text="Block Complete",
            variable=self.block_complete_var,
            command=self.on_block_complete_changed,
            font=("Arial", 9, "italic")
        )
        self.block_complete_check.pack(anchor="w", pady=(0, 5))

        # Create canvas and scrollbar for tasks
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, height=200)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add task button at bottom
        self.add_btn = tk.Button(
            self,
            text="+ Add Task",
            command=self.add_new_task,
            bg="#E8F5E9",
            relief="flat"
        )
        self.add_btn.pack(fill="x", pady=(5, 0))

    def populate_tasks(self):
        """Load tasks from block data into UI"""
        for task in self.block_data.tasks:
            self.add_task_item(task)

    def add_task_item(self, task):
        """Add a task item widget to the list"""
        task_item = TaskItem(
            self.scrollable_frame,
            task,
            on_change_callback=self.on_task_changed,
            on_delete_callback=self.delete_task_item
        )
        task_item.pack(fill="x", pady=2)
        self.task_items.append(task_item)

    def add_new_task(self):
        """Add a new empty task"""
        new_task = Task(text="")
        self.block_data.tasks.append(new_task)
        self.add_task_item(new_task)

        # Focus on the new task's entry
        if self.task_items:
            self.task_items[-1].text_entry.focus()

        if self.on_change_callback:
            self.on_change_callback()

    def delete_task_item(self, task_item):
        """Remove a task item from the list"""
        task = task_item.get_task()
        if task in self.block_data.tasks:
            self.block_data.tasks.remove(task)

        task_item.destroy()
        self.task_items.remove(task_item)

        if self.on_change_callback:
            self.on_change_callback()

    def on_block_complete_changed(self):
        """Handle block complete checkbox change"""
        self.block_data.block_completed = bool(self.block_complete_var.get())
        if self.on_change_callback:
            self.on_change_callback()

    def on_task_changed(self):
        """Handle any task change"""
        if self.on_change_callback:
            self.on_change_callback()

    def get_data(self):
        """Return block data with current task values"""
        # Update tasks from UI
        self.block_data.tasks = [item.get_task() for item in self.task_items]
        self.block_data.block_completed = bool(self.block_complete_var.get())
        return self.block_data

    def add_task(self, task):
        """Add an existing task (e.g., from queue)"""
        self.block_data.tasks.append(task)
        self.add_task_item(task)
        if self.on_change_callback:
            self.on_change_callback()

    def clear_tasks(self):
        """Clear all tasks from the block"""
        for item in self.task_items[:]:
            item.destroy()
        self.task_items.clear()
        self.block_data.tasks.clear()
        self.block_complete_var.set(0)
        self.block_data.block_completed = False
