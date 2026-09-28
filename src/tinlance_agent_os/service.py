"""OS-level task service.

This service composes work but delegates authority and execution to Agent Platform.
"""

from dataclasses import replace

from .domain import Task, TaskStatus
from .platform import AgentPlatformClient


class TaskService:
    def __init__(self, platform: AgentPlatformClient) -> None:
        self._platform = platform

    def start(self, task: Task) -> Task:
        run = self._platform.start_run(task)
        return replace(task, status=TaskStatus.RUNNING,
                       platform_run_ids=(*task.platform_run_ids, run.run_id))

    def cancel(self, task: Task) -> Task:
        if not task.platform_run_ids:
            return replace(task, status=TaskStatus.CANCELLED)
        self._platform.cancel_run(task.platform_run_ids[-1])
        return replace(task, status=TaskStatus.CANCELLED)
