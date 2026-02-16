# Daily Scheduler

Daily task scheduler GUI with 9 time blocks (Planning + 8 main blocks) for organizing your day.

## Features
- **Planning Block**: 20-minute planning section at top
- **8 Main Blocks**: 45-minute work blocks in grid layout
- **Task Queue**: Scrollable list for incomplete tasks that need rescheduling
- **Task Management**: Add, edit, complete, and delete tasks
- **Persistence**: Auto-saves every 30 seconds to local JSON files
- **Daily Reset**: "Start New Day" button to log completed tasks and move incomplete ones to queue
- **Statistics**: Tracks completed tasks, incomplete tasks, and daily completion rates

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/DocCyber/daily-scheduler.git
   cd daily-scheduler
   ```

2. Run the application:
   ```bash
   python main.py
   ```

   No external dependencies required - uses Python's built-in Tkinter.

## Usage

1. **Add Tasks**: Click "+ Add Task" buttons in any block to add new tasks
2. **Complete Tasks**: Check the checkbox when a task is done
3. **Mark Block Complete**: Use "Block Complete" checkbox when entire block is finished
4. **Queue Tasks**: Incomplete tasks from previous day appear in queue at bottom
5. **Move from Queue**: Click "→1" through "→8" buttons to move queued tasks to specific blocks
6. **Start New Day**: Click "Start New Day" to reset all blocks and move incomplete tasks to queue
7. **Save**: Click "Save" button or wait 30 seconds for auto-save

## Data Storage

All task data is stored locally in the `data/` directory:
- `tasks.json` - Current day's tasks and queue
- `completed_log.json` - Log of all completed tasks with timestamps
- `incomplete_history.json` - History of tasks moved to queue
- `daily_stats.json` - Daily completion statistics

**Note**: The `data/` directory is machine-specific and NOT synced to GitHub. Each machine maintains its own task lists.

## Project Structure

```
daily-scheduler/
├── main.py                    # Application entry point
├── src/
│   ├── data_manager.py        # JSON I/O and data persistence
│   ├── models/
│   │   ├── task.py           # Task data class
│   │   └── block.py          # Block data class
│   └── ui/
│       ├── main_window.py    # Main application window
│       ├── planning_block.py # Planning section widget
│       ├── task_block.py     # Task block widget
│       ├── task_item.py      # Individual task row
│       └── task_queue.py     # Queue widget
└── data/                      # Local data (git-ignored)
```

## License

Open source - use as you wish!
