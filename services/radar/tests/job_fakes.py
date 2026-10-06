"""Controlled job store and queue for failure and concurrency tests."""

import asyncio
from copy import deepcopy


class MemoryJobStore:
    def __init__(self):
        self.rows = {}
        self.lock = asyncio.Lock()
        self.fail_completion_once = False

    async def get(self, project_id, job_id):
        return deepcopy(self.rows.get((project_id, job_id)))

    async def list(self, project_id):
        return sorted((deepcopy(row) for (project, _), row in self.rows.items() if project == project_id),
                      key=lambda row: row.updated_at, reverse=True)[:50]

    async def change(self, project_id, job_id, transform):
        async with self.lock:
            result = transform(await self.get(project_id, job_id))
            if self.fail_completion_once and result.status == "completed":
                self.fail_completion_once = False
                raise RuntimeError("Simulated process loss before completion receipt")
            self.rows[(project_id, job_id)] = deepcopy(result)
            return deepcopy(result)


class MemoryTaskQueue:
    def __init__(self):
        self.tasks = {}
        self.fail_dispatch = False
        self.fail_lookup = False

    async def enqueue(self, job):
        if self.fail_dispatch:
            raise RuntimeError("Provider failure with secret-token-value")
        self.tasks.setdefault(job.task_name, deepcopy(job))

    async def exists(self, task_name):
        if self.fail_lookup:
            raise RuntimeError("Temporary provider failure")
        return task_name in self.tasks
