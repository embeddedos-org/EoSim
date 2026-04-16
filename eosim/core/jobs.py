# SPDX-License-Identifier: MIT
"""Job queue for simulation runs."""
import json
import os
import uuid
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Job:
    job_id: str = ""
    platform: str = ""
    engine: str = "eosim"
    status: str = "pending"


class JobQueue:
    def __init__(self, storage_dir: str):
        self._storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        return os.path.join(self._storage_dir, f"{job_id}.json")

    def submit(self, platform: str, engine: str = "eosim") -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            platform=platform,
            engine=engine,
            status="pending",
        )
        with open(self._job_path(job.job_id), "w") as f:
            json.dump(asdict(job), f)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        path = self._job_path(job_id)
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return Job(**data)

    def list_jobs(self) -> list[Job]:
        jobs = []
        for fname in os.listdir(self._storage_dir):
            if fname.endswith(".json"):
                path = os.path.join(self._storage_dir, fname)
                try:
                    with open(path) as f:
                        data = json.load(f)
                    jobs.append(Job(**data))
                except Exception:
                    pass
        return jobs

    def update(self, job_id: str, status: str = None) -> Optional[Job]:
        job = self.get(job_id)
        if job is None:
            return None
        if status is not None:
            job.status = status
        with open(self._job_path(job_id), "w") as f:
            json.dump(asdict(job), f)
        return job
