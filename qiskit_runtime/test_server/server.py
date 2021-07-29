"""
A test server with capabilities similar to
https://runtime-us-east.quantum-computing.ibm.com/openapi
"""

import json
import asyncio
from typing import List, Optional


from fastapi import FastAPI, Query, HTTPException, WebSocket
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FinishedJobRegistry, StartedJobRegistry, FailedJobRegistry
from qiskit.providers.ibmq.runtime import RuntimeDecoder
from qiskit_runtime.test_server.ioutils import (
    get_job_log_path,
    get_job_result_path,
    get_job_channel_id,
)


from .launcher import launch
from .metadata import load_metadata

_DEFAULT_SIMULATOR = "aer_simulator"
_STATUS_MAP = {
    "queued": "Queued",
    "started": "Running",
    "finished": "Completed",
    "stopped": "Cancelled",
    "failed": "Failed",
}
_PROGRAM_MAP = {
    "circuit-runner": "qiskit_runtime.circuit_runner.circuit_runner",
    "quantum-kernel-alignment": "qiskit_runtime.qka.qka",
    "vqe": "qiskit_runtime.vqe.vqe_program",
    "sample-program": "qiskit_runtime.sample_program.sample_program",
}
_DEFAULT_PROGRAM_TIMEOUT = 300

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


class ProgramResponse(BaseModel):
    name: str
    cost: Optional[int] = 600
    description: str
    version: Optional[str] = "1.0"
    backendRequirements: Optional[dict] = None
    parameters: Optional[List[dict]] = None
    returnValues: Optional[List[dict]] = None
    isPublic: Optional[bool] = True


class ProgramsResponse(BaseModel):
    programs: List[ProgramResponse]


@runtime.post("/jobs", tags=["jobs"])
def run_job(program_call: ProgramParams):
    program_module_path = _PROGRAM_MAP[program_call.programId]
    metadata = load_metadata(program_module_path)
    kwargs = json.loads(program_call.params[0], cls=RuntimeDecoder) if program_call.params else {}
    job = Job.create(
        launch,
        args=(program_module_path, _DEFAULT_SIMULATOR, kwargs),
        result_ttl=-1,
        failure_ttl=-1,
        timeout=metadata.get("max_execution_time", _DEFAULT_PROGRAM_TIMEOUT),
        connection=redis_conn,
    )
    job.meta["program_id"] = program_call.programId
    job.meta["log_path"] = get_job_log_path(job.id)
    job.meta["result_path"] = get_job_result_path(job.id)
    job.meta["channel_id"] = get_job_channel_id(job.id)
    job.save_meta()
    queue.enqueue_job(job)
    return {"id": job.id}


@runtime.get("/jobs", response_model=JobsResponse, tags=["jobs"])
def get_jobs(
    limit: int = Query(200, description="number of results to return at a time"),
    offset: int = Query(0, description="number of results to offset when retrieving list of jobs"),
    pending: bool = Query(
        False,
        description="returns 'Queued' and 'Running' jobs if "
        "true, returns 'Completed', 'Cancelled', 'Cancelled "
        "- Ran too long', and 'Failed' jobs if false",
    ),
):
    status = pending_status() if pending else finished_status()
    all_job_ids = (
        queue.get_job_ids() + started.get_job_ids()
        if pending
        else finished.get_job_ids() + failed.get_job_ids()
    )
    runtime_jobs = [to_job_response(queue.fetch_job(job_id)) for job_id in all_job_ids]
    filtered_jobs = [job for job in runtime_jobs if job.status in status]

    jobs = filtered_jobs[offset : offset + limit]
    count = len(jobs)

    return JobsResponse(jobs=jobs, count=count)


@runtime.get("/jobs/{job_id}", response_model=JobResponse, tags=["jobs"])
def get_job(job_id: str):
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return to_job_response(job)


@runtime.get("/jobs/{job_id}/logs", tags=["jobs"])
def get_job_logs(job_id: str):
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job.meta["log_path"], "r") as log_file:
        return log_file.read()


@runtime.get("/jobs/{job_id}/results", tags=["jobs"])
def get_job_results(job_id: str):
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        with open(job.meta["result_path"], "r") as result_file:
            return result_file.read()
    except OSError:
        return ""


@runtime.delete("/jobs/{job_id}", status_code=204, tags=["jobs"])
def delete_job(job_id: str):
    job = queue.fetch_job(job_id)
    if job:
        completed_job_ids = finished.get_job_ids() + failed.get_job_ids()
        if job_id in completed_job_ids:
            job.delete()
            return

        raise HTTPException(status_code=403, detail="Job not finalized")

    raise HTTPException(status_code=404, detail="Job not found")


@runtime.post("/jobs/{job_id}/cancel", status_code=204, tags=["jobs"])
def cancel_job(job_id: str):
    raise HTTPException(
        status_code=403, detail="Job not finalized. The test server cannot cancel jobs."
    )


@runtime.websocket("/stream/jobs/{job_id}")
async def stream_job_results(job_id: str, websocket: WebSocket):
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    await websocket.accept()
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(job.meta["channel_id"])

    while True:
        message = pubsub.get_message()
        if message and message["type"] == "message":
            _is_result, message_text = _get_message(message)
            # TODO: should we treat the message differently if it is a result?
            await websocket.send_text(message_text)
        else:
            await asyncio.sleep(0.1)


@runtime.get("/programs", response_model=ProgramsResponse, tags=["programs"])
def get_programs():
    all_program_modules = list(_PROGRAM_MAP.values())
    all_metadata = [to_program_response(program_module) for program_module in all_program_modules]
    return ProgramsResponse(programs=all_metadata)


@runtime.get("/programs/{program_id}", response_model=ProgramResponse, tags=["programs"])
def get_program(program_id: str):
    module_path = _PROGRAM_MAP.get(program_id)
    if not program_id:
        raise HTTPException(status_code=404, detail="Program not found")

    return to_program_response(module_path)


def to_job_response(job):
    _, backend, kwargs = job.args
    return JobResponse(
        id=job.id,
        hub="test-hub",
        group="test-group",
        project="test-project",
        backend=backend,
        status=_STATUS_MAP[job.get_status()],
        params=[json.dumps(kwargs)],
        program=job.meta["program_id"],
        created=job.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    )


def to_program_response(program_module_path):
    metadata = load_metadata(program_module_path)
    return ProgramResponse(**metadata)


def pending_status():
    return list(map(_STATUS_MAP.get, ["queued", "started"]))


def finished_status():
    return list(map(_STATUS_MAP.get, ["finished", "stopped", "failed"]))


def _get_message(message):
    redis_message = message["data"].decode("utf-8")
    message_type, message_text = redis_message.split(":", 1)
    return message_type == "result", message_text
