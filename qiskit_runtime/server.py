import json
from itertools import chain, islice
from typing import List
from fastapi import FastAPI, Query
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FinishedJobRegistry, StartedJobRegistry, FailedJobRegistry

from qiskit_runtime.launcher import launch

_DEFAULT_SIMULATOR = 'aer_simulator'
_STATUS_MAP = {
    'queued': 'Queued',
    'running': 'Running',
    'finished': 'Completed',
    'stopped': 'Cancelled',
    'failed': 'Failed',
}

redis_conn = Redis()
queue = Queue(connection=redis_conn)
finished = FinishedJobRegistry(queue=queue)
started = StartedJobRegistry(queue=queue)
failed = FailedJobRegistry(queue=queue)

runtime = FastAPI()

class ProgramParams(BaseModel):
    programId: str
    hub: str
    group: str
    project: str
    backend: str
    params: List[str]


class JobResponse(BaseModel):
    id: str
    hub: str
    group: str
    project: str
    backend: str
    status: str
    params: List[str]
    program: str
    created: str


class JobsResponse(BaseModel):
    jobs: List[JobResponse]
    count: int


@runtime.post('/jobs')
def run_job(program_call: ProgramParams):
    kwargs = json.loads(program_call.params[0]) if program_call.params else {}
    job = queue.enqueue(launch, program_call.programId, _DEFAULT_SIMULATOR, kwargs)
    return { 'id': job.id }


@runtime.get('/jobs', response_model=JobsResponse)
def get_jobs(
    limit: int = Query(200, description='number of results to return at a time'),
    offset: int = Query(0,description='number of results to offset when retrieving list of jobs'),
    pending: bool = Query(False, description="returns 'Queued' and 'Running' jobs if true, returns 'Completed', 'Cancelled', 'Cancelled - Ran too long', and 'Failed' jobs if false")
):
    status = pending_status() if pending else finished_status()
    all_job_ids = chain(
        finished.get_job_ids(),
        started.get_job_ids(),
        failed.get_job_ids()
    )
    runtime_jobs = map(to_job_response, map(queue.fetch_job, all_job_ids))
    filtered_jobs = (job for job in runtime_jobs if job.status in status)

    jobs = list(islice(filtered_jobs, offset, offset + limit))
    count = len(jobs)

    return JobsResponse(jobs=jobs, count=count)


def to_job_response(job):
    program_id, backend, kwargs = job.args
    return JobResponse(
        id=job.id,
        hub='test-hub',
        group='test-group',
        project='test-project',
        backend=backend,
        status=_STATUS_MAP[job.get_status()],
        params=[json.dumps(kwargs)],
        program=program_id,
        created=job.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    )


def pending_status():
    return map(_STATUS_MAP.get, ['queued', 'running'])


def finished_status():
    return map(_STATUS_MAP.get, ['finished', 'stopped', 'failed'])