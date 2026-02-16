from dataclasses import dataclass, field
from typing import List
from .task import Task

@dataclass
class Block:
    name: str
    tasks: List[Task] = field(default_factory=list)
    block_completed: bool = False

    def add_task(self, task_text: str):
        self.tasks.append(Task(text=task_text))

    def to_dict(self):
        return {
            'name': self.name,
            'tasks': [t.to_dict() for t in self.tasks],
            'block_completed': self.block_completed
        }

    @classmethod
    def from_dict(cls, data):
        tasks = [Task.from_dict(t) for t in data.get('tasks', [])]
        return cls(
            name=data['name'],
            tasks=tasks,
            block_completed=data.get('block_completed', False)
        )
