import tkinter as tk
from .task_item import TaskItem
from ..models.task import Task

class PlanningBlock(tk.LabelFrame):
    """Planning block widget - similar to TaskBlock but styled differently"""

    def __init__(self, parent, block_data, on_change_callback=None, move_callback=None):
        super().__init__(parent, text="Planning - 20 minutes",
                        font=("Arial", 12, "bold"), padx=10, pady=10,
                        bg="#5C4A00", fg="white", relief="ridge", borderwidth=2)
        self.block_data = block_data
        self.on_change_callback = on_change_callback
        self.move_callback = move_callback
        self.task_items = []

        self.create_widgets()
        self.populate_tasks()

    def create_widgets(self):
        """Create the planning block UI structure"""
        # Create canvas and scrollbar for tasks
        canvas_frame = tk.Frame(self, bg="#5C4A00")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, height=150, bg="#5C4A00")
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#5C4A00")
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
            text="+ Add Planning Item",
            command=self.add_new_task,
            bg="#7A6200",
            fg="white",
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
            on_delete_callback=self.delete_task_item,
            on_enter_callback=self.on_enter_in_task,
            show_move_buttons=self.move_callback is not None,
            move_callback=self.move_callback
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

    def remove_task(self, task):
        """Remove a task by object reference (used by move_from_planning callback)"""
        # Find the task_item whose task matches by text
        for task_item in list(self.task_items):
            if task_item.get_task().text == task.text:
                self.delete_task_item(task_item)
                return

    def on_task_changed(self):
        """Handle any task change"""
        if self.on_change_callback:
            self.on_change_callback()

    def on_enter_in_task(self, current_task_item):
        """Handle Enter key in a task - move to next field or create new task"""
        try:
            current_index = self.task_items.index(current_task_item)
            # If there's a next task, focus on it
            if current_index < len(self.task_items) - 1:
                self.task_items[current_index + 1].text_entry.focus()
            else:
                # Last task - create a new one
                self.add_new_task()
        except ValueError:
            pass

    def get_data(self):
        """Return block data with current task values"""
        self.block_data.tasks = [item.get_task() for item in self.task_items]
        return self.block_data

    def reload(self, block_data):
        """Replace block data and re-draw tasks (used after cloud sync)."""
        for item in self.task_items[:]:
            item.destroy()
        self.task_items.clear()
        self.block_data = block_data
        self.populate_tasks()

    def clear_tasks(self):
        """Clear all tasks from the planning block"""
        for item in self.task_items[:]:
            item.destroy()
        self.task_items.clear()
        self.block_data.tasks.clear()

    def set_highlight(self, is_active):
        """Set visual highlight when this block is active"""
        if is_active:
            self.config(borderwidth=4, relief="solid", bg="#FFEB3B", fg="#2C2C2C")
        else:
            self.config(borderwidth=2, relief="ridge", bg="#5C4A00", fg="white")
