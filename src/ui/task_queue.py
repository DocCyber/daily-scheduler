import tkinter as tk
from tkinter import messagebox

class TaskQueue(tk.Frame):
    """Scrollable queue widget for incomplete tasks"""

    def __init__(self, parent, queue_data, move_callback):
        super().__init__(parent)
        self.queue_data = queue_data
        self.move_callback = move_callback

        self.create_widgets()
        self.populate_queue()

    def create_widgets(self):
        """Create the scrollable queue UI"""
        # Create canvas and scrollbar
        canvas_frame = tk.Frame(self, bg="#7B1A1A")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, height=200, bg="#7B1A1A")
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#7B1A1A")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def populate_queue(self):
        """Display all queued tasks"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.queue_data:
            empty_label = tk.Label(
                self.scrollable_frame,
                text="Queue is empty",
                font=("Arial", 10, "italic"),
                fg="#AAAAAA",
                bg="#7B1A1A"
            )
            empty_label.pack(pady=20)
            return

        for task in self.queue_data:
            self.add_queue_item(task)

    def add_queue_item(self, task):
        """Add a single queue item with move buttons"""
        item_frame = tk.Frame(self.scrollable_frame, bg="#3A3A3A", relief="ridge", borderwidth=1)
        item_frame.pack(fill="x", padx=5, pady=2)

        # Task text (left side)
        task_label = tk.Label(
            item_frame,
            text=task.text,
            font=("Arial", 9),
            anchor="w",
            bg="#3A3A3A",
            fg="white"
        )
        task_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        # Times queued indicator
        if task.times_queued > 0:
            queue_count = tk.Label(
                item_frame,
                text=f"({task.times_queued}×)",
                font=("Arial", 8, "italic"),
                fg="#AAAAAA",
                bg="#3A3A3A"
            )
            queue_count.pack(side="left", padx=5)

        # Move to block buttons (right side)
        buttons_frame = tk.Frame(item_frame, bg="#3A3A3A")
        buttons_frame.pack(side="right", padx=5)

        for i in range(8):
            btn = tk.Button(
                buttons_frame,
                text=f"→{i+1}",
                command=lambda t=task, idx=i: self.move_to_block(t, idx),
                width=3,
                font=("Arial", 8),
                bg="#1A3A5C"
            )
            btn.pack(side="left", padx=1)

        # Delete button
        delete_btn = tk.Button(
            item_frame,
            text="×",
            command=lambda t=task: self.delete_from_queue(t),
            width=2,
            fg="#FF6B6B",
            bg="#3A3A3A"
        )
        delete_btn.pack(side="right", padx=5)

    def move_to_block(self, task, block_index):
        """Move task from queue to specified block"""
        if self.move_callback:
            self.move_callback(task, block_index)
            self.refresh(self.queue_data)

    def delete_from_queue(self, task):
        """Delete task from queue"""
        if messagebox.askyesno("Confirm Delete", f"Delete '{task.text}' from queue?"):
            self.queue_data.remove(task)
            self.refresh(self.queue_data)

    def refresh(self, queue_data):
        """Refresh the queue display"""
        self.queue_data = queue_data
        self.populate_queue()

    def get_data(self):
        """Return current queue data"""
        return self.queue_data
