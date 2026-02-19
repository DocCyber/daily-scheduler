import tkinter as tk
from tkinter import messagebox
from .planning_block import PlanningBlock
from .task_block import TaskBlock
from .task_queue import TaskQueue
from .timer_bar import TimerBar
from ..data_manager import DataManager
from ..timer_manager import TimerManager

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.geometry("840x540")  # Reduced by 40% from 1400x900

        # Read last-used dataset directly from home config (no full DataManager needed)
        import json
        from pathlib import Path
        try:
            _home_cfg = Path("data") / "config.json"
            self.active_dataset = json.loads(_home_cfg.read_text()).get("active_dataset", "home") if _home_cfg.exists() else "home"
        except Exception:
            self.active_dataset = "home"
        _label = "Work" if self.active_dataset == "work" else "Home"
        self.title(f"Daily Scheduler [{_label}]")
        data_dir = "data-work" if self.active_dataset == "work" else "data"
        self.data_manager = DataManager(data_dir=data_dir)
        # Work is always local-only — disable sync regardless of config
        if self.active_dataset == "work":
            self.data_manager.cloudflare_sync.enabled = False
        self.load_data()

        # Initialize timer manager (before create_widgets so UI can reference it)
        self.timer_manager = TimerManager(
            data_manager=self.data_manager,
            root_window=self,
            on_state_change_callback=self.on_timer_state_changed
        )

        self._highlighted_phase = None

        self.create_widgets()
        self.bind_events()

        # Validate timer configuration on startup
        if not self.timer_manager.validate_config():
            messagebox.showwarning(
                "Timer Configuration",
                "Voice Monkey is not configured.\n\n"
                "To enable announcements:\n"
                "1. Copy data/config.example.json to data/config.json\n"
                "2. Add your Voice Monkey API URL\n\n"
                "Timer will work without announcements."
            )

        # Auto-download from cloud on startup (home dataset only)
        if self.active_dataset == "home" and self.data_manager.cloudflare_sync.worker_url:
            print("[Startup] Downloading latest data from cloud...")
            self.after(1000, self.startup_sync)  # Delay 1 second to let UI load

    def load_data(self):
        """Load tasks from JSON"""
        data = self.data_manager.load_tasks()
        self.planning_data = data['planning']
        self.blocks_data = data['blocks']
        self.queue_data = data['queue']

    def create_widgets(self):
        """Build UI layout"""
        # Main container with scrollbar
        main_container = tk.Frame(self, bg="#2C2C2C")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create canvas for scrolling
        canvas = tk.Canvas(main_container, bg="#2C2C2C", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2C2C2C")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Store canvas reference for mouse wheel binding
        self.main_canvas = canvas

        # Main frame inside scrollable area
        main_frame = tk.Frame(scrollable_frame, bg="#2C2C2C")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Store main_frame for responsive layout
        self.main_frame = main_frame

        # Timer bar at top (spans full width)
        self.timer_bar = TimerBar(
            main_frame,
            self.timer_manager,
            dataset_callback=self.switch_dataset,
            active_dataset=self.active_dataset
        )

        # Planning block below timer (spans full width)
        self.planning_block = PlanningBlock(main_frame, self.planning_data, self.on_data_changed,
                                            move_callback=self.move_from_planning)

        # Create blocks (will be arranged by reorganize_blocks)
        self.block_widgets = []
        for i in range(8):
            block_widget = TaskBlock(main_frame, self.blocks_data[i], self.on_data_changed)
            self.block_widgets.append(block_widget)

        # Start with 2 columns (for 840px default width)
        self.current_columns = 2

        # Queue at bottom - store reference
        self.queue_frame = tk.Frame(main_frame, relief="sunken", borderwidth=2, bg="#7B1A1A")

        queue_label = tk.Label(
            self.queue_frame,
            text="Task Queue (Incomplete Tasks)",
            font=("Arial", 12, "bold"),
            bg="#7B1A1A",
            fg="white",
            pady=5
        )
        queue_label.pack(fill="x")

        self.task_queue = TaskQueue(self.queue_frame, self.queue_data, self.move_from_queue, self.move_from_queue_to_planning)
        self.task_queue.pack(fill=tk.BOTH, expand=True)

        # Initial layout
        self.reorganize_blocks(2)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Control buttons at bottom
        button_frame = tk.Frame(self, bg="#2C2C2C")
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

        # Sync Now button (always shown; disabled if no worker URL configured)
        sync_configured = bool(self.data_manager.cloudflare_sync.worker_url)
        self.sync_btn = tk.Button(
            button_frame,
            text="☁ Sync Now",
            command=self.sync_now,
            bg="#2196F3" if sync_configured else "#555555",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            state="normal" if sync_configured else "disabled"
        )
        # Only show sync button on Home dataset
        if self.active_dataset != "work":
            self.sync_btn.pack(side=tk.LEFT, padx=5, pady=10)

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
            bg="#2C2C2C",
            fg="#AAAAAA"
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
        # Adjusted breakpoints to prevent early switching
        if width < 600:
            columns = 1
        elif width < 900:
            columns = 2
        elif width < 1200:
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

        # Remove timer bar, planning block and queue
        self.timer_bar.grid_forget()
        self.planning_block.grid_forget()
        self.queue_frame.grid_forget()

        # Re-grid timer bar at top (spans all columns)
        self.timer_bar.grid(row=0, column=0, columnspan=columns, sticky="ew", pady=(0, 5))

        # Re-grid planning block (spans all columns)
        self.planning_block.grid(row=1, column=0, columnspan=columns, sticky="ew", pady=(0, 10))

        # Re-grid blocks (starting at row 2, after timer bar and planning)
        for i, block_widget in enumerate(self.block_widgets):
            row = (i // columns) + 2  # +2 for timer bar and planning block
            col = i % columns
            block_widget.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)

        # Calculate queue row (after all block rows + timer bar + planning block)
        num_block_rows = (8 + columns - 1) // columns
        queue_row = num_block_rows + 2  # +2 for timer bar and planning block

        # Re-grid queue at bottom (spans all columns)
        self.queue_frame.grid(row=queue_row, column=0, columnspan=columns, sticky="ew", pady=(10, 0))

        # Update grid column weights
        # First, reset all column weights
        for i in range(10):  # Clear old weights
            self.main_frame.grid_columnconfigure(i, weight=0)
        # Set new weights
        for i in range(columns):
            self.main_frame.grid_columnconfigure(i, weight=1)

        # Update row weights (rows needed = ceiling(8 blocks / columns))
        for i in range(1, num_block_rows + 1):
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

    def on_timer_state_changed(self, timer_state):
        """Called when timer state changes - update UI"""
        self.timer_bar.update_display(timer_state)
        self.highlight_active_block(timer_state.current_phase)

    def highlight_active_block(self, current_phase):
        """Highlight the currently active block with colored border"""
        # Skip all work if the phase hasn't changed
        if current_phase == self._highlighted_phase:
            return

        # Remove highlight from the previously active widget only
        prev = self._highlighted_phase
        if prev == "Planning":
            self.planning_block.set_highlight(False)
        elif prev and prev.startswith("Block"):
            try:
                self.block_widgets[int(prev.split()[1]) - 1].set_highlight(False)
            except (IndexError, ValueError):
                pass
        else:
            # First call or unknown previous state — clear everything once
            self.planning_block.set_highlight(False)
            for block_widget in self.block_widgets:
                block_widget.set_highlight(False)

        self._highlighted_phase = current_phase

        # Highlight the new active block
        if current_phase == "Planning":
            self.planning_block.set_highlight(True)
        elif current_phase.startswith("Block"):
            try:
                self.block_widgets[int(current_phase.split()[1]) - 1].set_highlight(True)
            except (IndexError, ValueError):
                pass

    def start_new_day(self):
        """Move incomplete tasks to queue and reset timer"""
        if not messagebox.askyesno("Confirm",
            "Start a new day?\n\nAll incomplete tasks will move to the queue.\nCompleted tasks will be logged.\nTimer will be reset."):
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

        # Reset timer
        self.timer_manager.reset()
        self.data_manager.clear_timer_state()

        # Save
        self.save_data(silent=True)

        messagebox.showinfo("New Day Started",
            f"Completed: {completed_tasks}/{total_tasks} tasks\n"
            f"Moved {total_tasks - completed_tasks} tasks to queue\n"
            f"Timer reset to Planning")

    def move_from_queue(self, task, target_block_index):
        """Move task from queue to specified block"""
        # Remove from queue data
        if task in self.queue_data:
            self.queue_data.remove(task)

        # Add to target block
        self.block_widgets[target_block_index].add_task(task)

        # Save
        self.save_data(silent=True)

    def move_from_queue_to_planning(self, task):
        """Move task from queue to planning block"""
        if task in self.queue_data:
            self.queue_data.remove(task)

        # Add to planning block
        self.planning_block.block_data.tasks.append(task)
        self.planning_block.add_task_item(task)

        # Save
        self.save_data(silent=True)

    def move_from_planning(self, task, target_block_index):
        """Move task from planning block to specified block"""
        # Remove from planning (widget handles its own list + block_data)
        self.planning_block.remove_task(task)

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

    def sync_now(self):
        """Manually trigger cloud sync"""
        # Show confirmation before syncing
        confirm = messagebox.askyesno(
            "Sync to Cloud",
            "This will upload your local data and download any cloud updates.\n\n"
            "Continue?"
        )

        if not confirm:
            return

        # Disable button during sync
        self.sync_btn.config(state="disabled", text="Syncing...")
        self.update()

        try:
            success = self.data_manager.sync_to_cloud()

            if success:
                self.reload_from_disk()
                messagebox.showinfo("Sync Complete",
                    "Data synced to cloud and display updated!")
            else:
                messagebox.showwarning(
                    "Sync Issues",
                    "Sync completed with some errors. Check console for details."
                )
        except Exception as e:
            messagebox.showerror("Sync Failed", f"Error during sync: {e}")
        finally:
            if self.active_dataset != "work":
                sync_configured = bool(self.data_manager.cloudflare_sync.worker_url)
                self.sync_btn.config(
                    state="normal" if sync_configured else "disabled",
                    bg="#2196F3" if sync_configured else "#555555",
                    text="☁ Sync Now"
                )

    def startup_sync(self):
        """Download latest cloud data and hot-reload UI on startup."""
        try:
            self.data_manager.download_from_cloud()
            print("[Startup] Cloud data downloaded - reloading UI...")
            self.reload_from_disk()
            print("[Startup] UI reloaded with cloud data")
        except Exception as e:
            print(f"[Startup] Failed to download cloud data: {e}")
            # Continue with local data as-is

    def reload_from_disk(self):
        """Re-read tasks.json from disk and refresh all widgets in-place."""
        data = self.data_manager.load_tasks()
        self.planning_data = data['planning']
        self.blocks_data = data['blocks']
        self.queue_data = data['queue']

        self.planning_block.reload(self.planning_data)

        for i, block_widget in enumerate(self.block_widgets):
            block_widget.reload(self.blocks_data[i])

        self.task_queue.refresh(self.queue_data)

    def switch_dataset(self, mode: str):
        """Switch between 'home' and 'work' datasets on the fly."""
        if mode == self.active_dataset:
            return

        # Save current data first
        self.save_data(silent=True)

        # Stop timer tick
        self.timer_manager._cancel_tick()

        # Rebuild DataManager and TimerManager for new dataset
        data_dir = "data-work" if mode == "work" else "data"
        self.active_dataset = mode
        self.data_manager = DataManager(data_dir=data_dir)
        # Work is always local-only — disable sync regardless of config
        if mode == "work":
            self.data_manager.cloudflare_sync.enabled = False
        self.timer_manager = TimerManager(
            data_manager=self.data_manager,
            root_window=self,
            on_state_change_callback=self.on_timer_state_changed
        )

        # Reset highlight and timer bar cache for fresh state
        self._highlighted_phase = None
        self.timer_bar._current_bg_color = None
        self.timer_bar._last_is_running = None

        # Point timer bar at the new timer manager and refresh dataset radio
        self.timer_bar.timer_manager = self.timer_manager
        self.timer_bar.set_dataset(mode)

        # Reload tasks and timer UI
        self.reload_from_disk()
        self.on_timer_state_changed(self.timer_manager.timer_state)

        # Show/hide sync button (work = hidden, home = visible)
        if mode == "work":
            self.sync_btn.pack_forget()
        else:
            sync_configured = bool(self.data_manager.cloudflare_sync.worker_url)
            self.sync_btn.config(
                state="normal" if sync_configured else "disabled",
                bg="#2196F3" if sync_configured else "#555555"
            )
            self.sync_btn.pack(side=tk.LEFT, padx=5, pady=10)

        # Persist choice to home config
        self.data_manager.save_active_dataset(mode)

        # Update window title to show active dataset
        label = "Work" if mode == "work" else "Home"
        self.title(f"Daily Scheduler [{label}]")
