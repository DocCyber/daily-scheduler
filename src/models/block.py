from dataclasses import dataclass, field
from typing import List
from .task import Task

@dataclass
class Block:
    name: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task_text: str):
        self.tasks.append(Task(text=task_text))

    def to_dict(self):
        return {
            'name': self.name,
            'tasks': [t.to_dict() for t in self.tasks]
        }

    @classmethod
    def from_dict(cls, data):
        tasks = [Task.from_dict(t) for t in data.get('tasks', [])]
        return cls(
            name=data['name'],
            tasks=tasks
        )
