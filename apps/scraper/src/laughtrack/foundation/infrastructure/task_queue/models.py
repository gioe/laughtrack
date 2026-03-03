"""Infrastructure task queue utilities."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from laughtrack.foundation.models.types import JSONDict


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Representation of a background task."""

    id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: JSONDict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class TaskQueue:
    """
    Infrastructure utility for managing background tasks and job queues.
    """

    def __init__(self, max_workers: int = 5):
        """
        Initialize task queue.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.tasks: Dict[str, Task] = {}
        self.max_workers = max_workers
        self._workers_started = False
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def create_task_id() -> str:
        """
        Generate a unique task ID.

        Returns:
            Unique task ID string
        """
        return str(uuid.uuid4())

    @staticmethod
    def is_task_completed(task: Task) -> bool:
        """
        Check if a task is completed (either successfully or failed).

        Args:
            task: Task to check

        Returns:
            True if task is completed, False otherwise
        """
        return task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    @staticmethod
    def is_task_active(task: Task) -> bool:
        """
        Check if a task is currently active (pending or running).

        Args:
            task: Task to check

        Returns:
            True if task is active, False otherwise
        """
        return task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)

    @staticmethod
    def get_task_duration(task: Task) -> Optional[float]:
        """
        Get the duration of a task in seconds.

        Args:
            task: Task to get duration for

        Returns:
            Duration in seconds, or None if task hasn't started or completed
        """
        if not task.started_at:
            return None

        end_time = task.completed_at or datetime.now()
        return (end_time - task.started_at).total_seconds()

    @staticmethod
    def filter_tasks_by_status(tasks: Dict[str, Task], status: TaskStatus) -> Dict[str, Task]:
        """
        Filter tasks by their status.

        Args:
            tasks: Dictionary of tasks to filter
            status: Status to filter by

        Returns:
            Dictionary of tasks with matching status
        """
        return {task_id: task for task_id, task in tasks.items() if task.status == status}

    def add_task(self, func: Callable, *args, task_id: Optional[str] = None, max_retries: int = 3, **kwargs) -> str:
        """
        Add a task to the queue.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            task_id: Optional specific task ID
            max_retries: Maximum number of retry attempts
            **kwargs: Keyword arguments for function

        Returns:
            Task ID
        """
        if task_id is None:
            task_id = self.create_task_id()

        task = Task(id=task_id, func=func, args=args, kwargs=kwargs, max_retries=max_retries)

        self.tasks[task_id] = task
        self.logger.info(f"Added task {task_id} to queue")

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task object or None if not found
        """
        return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled, False if not found or already running
        """
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.logger.info(f"Cancelled task {task_id}")
            return True
        return False

    def get_pending_tasks(self) -> Dict[str, Task]:
        """Get all pending tasks."""
        return self.filter_tasks_by_status(self.tasks, TaskStatus.PENDING)

    def get_running_tasks(self) -> Dict[str, Task]:
        """Get all running tasks."""
        return self.filter_tasks_by_status(self.tasks, TaskStatus.RUNNING)

    def get_completed_tasks(self) -> Dict[str, Task]:
        """Get all completed tasks."""
        return self.filter_tasks_by_status(self.tasks, TaskStatus.COMPLETED)

    def get_failed_tasks(self) -> Dict[str, Task]:
        """Get all failed tasks."""
        return self.filter_tasks_by_status(self.tasks, TaskStatus.FAILED)

    async def execute_task(self, task: Task) -> None:
        """
        Execute a single task.

        Args:
            task: Task to execute
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.logger.info(f"Starting task {task.id}")

        try:
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = task.func(*task.args, **task.kwargs)

            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.logger.info(f"Task {task.id} completed successfully")

        except Exception as e:
            task.error = str(e)
            task.retry_count += 1

            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.PENDING
                self.logger.warning(f"Task {task.id} failed, retry {task.retry_count}/{task.max_retries}: {e}")
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                self.logger.error(f"Task {task.id} failed permanently after {task.retry_count} retries: {e}")

    async def process_queue(self) -> None:
        """Process all pending tasks in the queue."""
        pending_tasks = list(self.get_pending_tasks().values())

        if not pending_tasks:
            return

        # Process tasks with worker limit
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(task: Task):
            async with semaphore:
                await self.execute_task(task)

        # Execute tasks concurrently
        await asyncio.gather(*[process_with_semaphore(task) for task in pending_tasks])

    def clear_completed_tasks(self) -> int:
        """
        Remove completed and failed tasks from the queue.

        Returns:
            Number of tasks cleared
        """
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.tasks[task_id]

        self.logger.info(f"Cleared {len(tasks_to_remove)} completed tasks")
        return len(tasks_to_remove)

    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get statistics about the task queue.

        Returns:
            Dictionary with queue statistics
        """
        stats = {"total": len(self.tasks), "pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}

        for task in self.tasks.values():
            stats[task.status.value] += 1

        return stats
