from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Task(BaseModel):
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    command: Optional[Dict[str, Any]] = None
    agent_hint: Optional[str] = None


class TaskGraph(BaseModel):
    tasks: Dict[str, Task] = Field(default_factory=dict)

    def add_task(self, task: Task) -> None:
        if task.id in self.tasks:
            raise ValueError(f"Task with id {task.id} already exists")
        self.tasks[task.id] = task

    def get_ready_tasks(self) -> List[Task]:
        """
        Возвращает задачи, готовые к выполнению (все зависимости завершены).
        Зависимости с несуществующим id считаются не выполненными (задача не готова).
        """
        ready: List[Task] = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if all(
                dep in self.tasks and self.tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
            ):
                ready.append(task)
        return ready

