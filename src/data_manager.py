import json
from pathlib import Path
from typing import List, Dict, Optional
from .models.task import Task
from .models.block import Block
from .models.timer_state import TimerState
from .integrations.cloudflare_sync import CloudflareSync

class DataManager:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.tasks_file = self.data_dir / "tasks.json"
        self.completed_log_file = self.data_dir / "completed_log.json"
        self.incomplete_history_file = self.data_dir / "incomplete_history.json"
        self.daily_stats_file = self.data_dir / "daily_stats.json"
        self.timer_state_file = self.data_dir / "timer_state.json"
        self.config_file = self.data_dir / "config.json"

        # Initialize Cloudflare sync client
        config = self.load_config()
        sync_config = config.get("cloudflare_sync", {})
        self.cloudflare_sync = CloudflareSync(
            worker_url=sync_config.get("worker_url", ""),
            data_dir=self.data_dir,
            enabled=sync_config.get("enabled", False)
        )

    def load_tasks(self) -> Dict:
        """Load current tasks and queue"""
        if self.tasks_file.exists():
            data = json.loads(self.tasks_file.read_text())
            # Convert dicts back to Block/Task objects
            return {
                'planning': Block.from_dict(data.get('planning', {'name': 'Planning', 'tasks': []})),
                'blocks': [Block.from_dict(b) for b in data.get('blocks', [])],
                'queue': [Task.from_dict(t) for t in data.get('queue', [])]
            }

        # Default structure
        return {
            'planning': Block(name="Planning"),
            'blocks': [Block(name=f"Block {i+1}") for i in range(8)],
            'queue': []
        }

    def save_tasks(self, planning: Block, blocks: List[Block], queue: List[Task]):
        """Save current tasks and queue"""
        data = {
            'planning': planning.to_dict(),
            'blocks': [b.to_dict() for b in blocks],
            'queue': [t.to_dict() for t in queue]
        }
        self.tasks_file.write_text(json.dumps(data, indent=2))

    def log_completed_task(self, task: Task, block_name: str):
        """Append completed task to log"""
        log = []
        if self.completed_log_file.exists():
            log = json.loads(self.completed_log_file.read_text())

        log.append({
            'task': task.text,
            'block': block_name,
            'completed_at': task.completed_at,
            'times_queued': task.times_queued
        })

        self.completed_log_file.write_text(json.dumps(log, indent=2))

    def log_incomplete_task(self, task: Task, original_block: str):
        """Track incomplete task moved to queue"""
        history = []
        if self.incomplete_history_file.exists():
            history = json.loads(self.incomplete_history_file.read_text())

        task.times_queued += 1
        history.append({
            'task': task.text,
            'original_block': original_block,
            'queued_count': task.times_queued,
            'queued_at': task.created_at
        })

        self.incomplete_history_file.write_text(json.dumps(history, indent=2))

    def update_daily_stats(self, completed_count: int, total_count: int):
        """Save daily completion statistics"""
        from datetime import datetime
        stats = []
        if self.daily_stats_file.exists():
            stats = json.loads(self.daily_stats_file.read_text())

        stats.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'completed': completed_count,
            'total': total_count,
            'completion_rate': round(completed_count / total_count * 100, 1) if total_count > 0 else 0
        })

        self.daily_stats_file.write_text(json.dumps(stats, indent=2))

    def load_timer_state(self) -> Optional[TimerState]:
        """Load timer state from persistence."""
        if self.timer_state_file.exists():
            try:
                data = json.loads(self.timer_state_file.read_text())
                return TimerState.from_dict(data)
            except Exception as e:
                print(f"Error loading timer state: {e}")
                return None
        return None

    def save_timer_state(self, timer_state: TimerState):
        """Save timer state to persistence."""
        try:
            self.timer_state_file.write_text(
                json.dumps(timer_state.to_dict(), indent=2)
            )
        except Exception as e:
            print(f"Error saving timer state: {e}")

    def clear_timer_state(self):
        """Clear timer state (used when starting new day)."""
        if self.timer_state_file.exists():
            self.timer_state_file.unlink()

    def load_config(self) -> Dict:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._default_config()
        return self._default_config()

    def save_config(self, config: Dict):
        """Save configuration to file."""
        try:
            self.config_file.write_text(json.dumps(config, indent=2))
        except Exception as e:
            print(f"Error saving config: {e}")

    def _default_config(self) -> Dict:
        """Return default configuration."""
        return {
            "voice_monkey": {
                "api_url": ""
            },
            "timer": {
                "auto_advance": True,
                "enable_announcements": True,
                "warning_at_minutes": [5, 2]
            },
            "cloudflare_sync": {
                "enabled": False,
                "worker_url": "",
                "auto_sync_on_startup": True
            }
        }

    def sync_to_cloud(self) -> bool:
        """Sync data to Cloudflare R2 (upload then download)."""
        return self.cloudflare_sync.sync()

    def download_from_cloud(self) -> Dict[str, int]:
        """Download latest data from cloud."""
        return self.cloudflare_sync.download_all()
