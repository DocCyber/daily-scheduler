import json
from pathlib import Path
from typing import List, Dict
from .models.task import Task
from .models.block import Block

class DataManager:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.tasks_file = self.data_dir / "tasks.json"
        self.completed_log_file = self.data_dir / "completed_log.json"
        self.incomplete_history_file = self.data_dir / "incomplete_history.json"
        self.daily_stats_file = self.data_dir / "daily_stats.json"

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
