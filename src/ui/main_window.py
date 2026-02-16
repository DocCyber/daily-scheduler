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

        # Store canvas reference for mouse wheel binding
        self.main_canvas = canvas

        # Main frame inside scrollable area
        main_frame = tk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Store main_frame for responsive layout
        self.main_frame = main_frame

        # Planning block at top (spans full width)
        self.planning_block = PlanningBlock(main_frame, self.planning_data, self.on_data_changed)

        # Create blocks (will be arranged by reorganize_blocks)
        self.block_widgets = []
        for i in range(8):
            block_widget = TaskBlock(main_frame, self.blocks_data[i], self.on_data_changed)
            self.block_widgets.append(block_widget)

        # Start with 2 columns (for 840px default width)
        self.current_columns = 2
        self.reorganize_blocks(2)

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
        """Set up auto-save on task changes and mouse wheel scrolling"""
        # Auto-save every 30 seconds
        self.after(30000, self.auto_save)

        # Enable mouse wheel scrolling on the main canvas
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.main_canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.main_canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux scroll down

        # Bind window resize to reorganize blocks
        self.bind("<Configure>", self._on_window_resize)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 5 or event.delta < 0:
            # Scroll down
            self.main_canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            # Scroll up
            self.main_canvas.yview_scroll(-1, "units")

    def _on_window_resize(self, event):
        """Handle window resize - reorganize blocks based on width"""
        # Only respond to main window resize, not child widgets
        if event.widget != self:
            return

        width = event.width

        # Determine columns based on window width
        # <500px: 1 column, 500-700px: 2 columns, 700-1000px: 3 columns, >1000px: 4 columns
        if width < 500:
            columns = 1
        elif width < 700:
            columns = 2
        elif width < 1000:
            columns = 3
        else:
            columns = 4

        # Only reorganize if column count changed
        if columns != self.current_columns:
            self.current_columns = columns
            self.reorganize_blocks(columns)

    def reorganize_blocks(self, columns):
        """Reorganize blocks into specified number of columns"""
        # Remove all blocks from grid
        for widget in self.block_widgets:
            widget.grid_forget()

        # Remove planning block
        self.planning_block.grid_forget()

        # Re-grid planning block (spans all columns)
        self.planning_block.grid(row=0, column=0, columnspan=columns, sticky="ew", pady=(0, 10))

        # Re-grid blocks
        for i, block_widget in enumerate(self.block_widgets):
            row = (i // columns) + 1
            col = i % columns
            block_widget.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)

        # Update grid column weights
        # First, reset all column weights
        for i in range(10):  # Clear old weights
            self.main_frame.grid_columnconfigure(i, weight=0)
        # Set new weights
        for i in range(columns):
            self.main_frame.grid_columnconfigure(i, weight=1)

        # Update row weights (rows needed = ceiling(8 blocks / columns))
        num_rows = (8 + columns - 1) // columns
        for i in range(1, num_rows + 1):
            self.main_frame.grid_rowconfigure(i, weight=1)

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
