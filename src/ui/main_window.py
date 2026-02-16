import tkinter as tk
from tkinter import messagebox
from .planning_block import PlanningBlock
from .task_block import TaskBlock
from .task_queue import TaskQueue
from ..data_manager import DataManager

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Daily Scheduler")
        self.geometry("840x540")  # Reduced by 40% from 1400x900

        self.data_manager = DataManager()
        self.load_data()

        self.create_widgets()
        self.bind_events()

    def load_data(self):
        """Load tasks from JSON"""
        data = self.data_manager.load_tasks()
        self.planning_data = data['planning']
        self.blocks_data = data['blocks']
        self.queue_data = data['queue']

    def create_widgets(self):
        """Build UI layout"""
        # Main container with scrollbar
        main_container = tk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Main frame inside scrollable area
        main_frame = tk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Planning block at top
        self.planning_block = PlanningBlock(main_frame, self.planning_data, self.on_data_changed)
        self.planning_block.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        # 8 blocks in grid layout
        # Row 1: Blocks 1, 2, 3
        # Row 2: Blocks 4, 5, 6
        # Row 3: Blocks 7, 8, (empty)
        self.block_widgets = []
        positions = [
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2),
            (3, 0), (3, 1)
        ]

        for i, (row, col) in enumerate(positions):
            block_widget = TaskBlock(main_frame, self.blocks_data[i], self.on_data_changed)
            block_widget.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            self.block_widgets.append(block_widget)

        # Configure grid weights for resizing
        for i in range(1, 4):
            main_frame.grid_rowconfigure(i, weight=1)
        for i in range(3):
            main_frame.grid_columnconfigure(i, weight=1)

        # Queue at bottom
        queue_frame = tk.Frame(main_frame, relief="sunken", borderwidth=2)
        queue_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        queue_label = tk.Label(
            queue_frame,
            text="Task Queue (Incomplete Tasks)",
            font=("Arial", 12, "bold"),
            bg="#FFCDD2",
            pady=5
        )
        queue_label.pack(fill="x")

        self.task_queue = TaskQueue(queue_frame, self.queue_data, self.move_from_queue)
        self.task_queue.pack(fill=tk.BOTH, expand=True)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Control buttons at bottom
        button_frame = tk.Frame(self, bg="#E0E0E0")
        button_frame.pack(fill=tk.X, padx=0, pady=0)

        tk.Button(
            button_frame,
            text="Start New Day",
            command=self.start_new_day,
            bg="#FF6B6B",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8
        ).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Button(
            button_frame,
            text="Save",
            command=self.save_data,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11),
            padx=20,
            pady=8
        ).pack(side=tk.LEFT, padx=5, pady=10)

        tk.Button(
            button_frame,
            text="Exit",
            command=self.quit_app,
            font=("Arial", 11),
            padx=20,
            pady=8
        ).pack(side=tk.RIGHT, padx=10, pady=10)

        # Status label
        self.status_label = tk.Label(
            button_frame,
            text="Ready",
            font=("Arial", 9),
            bg="#E0E0E0",
            fg="gray"
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

    def bind_events(self):
        """Set up auto-save on task changes"""
        # Auto-save every 30 seconds
        self.after(30000, self.auto_save)

    def auto_save(self):
        """Background auto-save"""
        self.save_data(silent=True)
        self.after(30000, self.auto_save)

    def on_data_changed(self):
        """Called when any data changes in the UI - auto-save immediately"""
        self.save_data(silent=True)

    def save_data(self, silent=False):
        """Save all tasks to JSON"""
        try:
            # Collect data from widgets
            planning = self.planning_block.get_data()
            blocks = [b.get_data() for b in self.block_widgets]
            queue = self.task_queue.get_data()

            self.data_manager.save_tasks(planning, blocks, queue)

            self.status_label.config(text="Saved", fg="green")

            if not silent:
                messagebox.showinfo("Saved", "Tasks saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def start_new_day(self):
        """Move incomplete tasks to queue"""
        if not messagebox.askyesno("Confirm",
            "Start a new day?\n\nAll incomplete tasks will move to the queue.\nCompleted tasks will be logged."):
            return

        # Count stats before clearing
        total_tasks = 0
        completed_tasks = 0

        # Process all blocks (including planning)
        all_block_widgets = [self.planning_block] + self.block_widgets

        for block_widget in all_block_widgets:
            block_data = block_widget.get_data()
            block_name = block_data.name

            for task in block_data.tasks:
                if task.text.strip():  # Only count non-empty tasks
                    total_tasks += 1
                    if task.completed:
                        completed_tasks += 1
                        # Log completed task
                        self.data_manager.log_completed_task(task, block_name)
                    else:
                        # Move to queue
                        self.data_manager.log_incomplete_task(task, block_name)
                        self.queue_data.append(task)

            # Clear block
            block_widget.clear_tasks()

        # Update stats
        if total_tasks > 0:
            self.data_manager.update_daily_stats(completed_tasks, total_tasks)

        # Refresh queue display
        self.task_queue.refresh(self.queue_data)

        # Save
        self.save_data(silent=True)

        messagebox.showinfo("New Day Started",
            f"Completed: {completed_tasks}/{total_tasks} tasks\n"
            f"Moved {total_tasks - completed_tasks} tasks to queue")

    def move_from_queue(self, task, target_block_index):
        """Move task from queue to specified block"""
        # Remove from queue data
        if task in self.queue_data:
            self.queue_data.remove(task)

        # Add to target block
        self.block_widgets[target_block_index].add_task(task)

        # Save
        self.save_data(silent=True)

    def quit_app(self):
        """Exit with save prompt"""
        if self.status_label.cget("text") == "Unsaved changes":
            result = messagebox.askyesnocancel("Exit", "Save before exiting?")
            if result is None:  # Cancel
                return
            elif result:  # Yes
                self.save_data(silent=True)

        self.quit()
