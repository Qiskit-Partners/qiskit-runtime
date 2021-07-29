# This code is part of qiskit-runtime.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
A test server with capabilities similar to
https://runtime-us-east.quantum-computing.ibm.com/openapi
"""

import json
from typing import List, Optional


from fastapi import FastAPI, Query, HTTPException, WebSocket, status
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FinishedJobRegistry, StartedJobRegistry, FailedJobRegistry
import aioredis

from qiskit.providers.ibmq.runtime import RuntimeDecoder
from qiskit_runtime.test_server.jobids import (
    get_job_log_path,
    get_job_result_path,
    get_job_channel_id,
)

from .launcher import launch
from .metadata import all_programs, load_metadata, resolve_program_module_path

_DEFAULT_SIMULATOR = "aer_simulator"
_STATUS_MAP = {
    "queued": "Queued",
    "started": "Running",
    "finished": "Completed",
    "stopped": "Cancelled",
    "failed": "Failed",
}

redis_client = Redis()
queue = Queue(connection=redis_client)
finished = FinishedJobRegistry(queue=queue)
started = StartedJobRegistry(queue=queue)
failed = FailedJobRegistry(queue=queue)

runtime = FastAPI()


class ProgramParams(BaseModel):
    """Configuration and input data for scheduling a program execution."""

    programId: str
    hub: str
    group: str
    project: str
    backend: str
    params: List[str]


class JobResponse(BaseModel):
    """Execution, configuration and input data of a program."""

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
    """List of jobs."""

    jobs: List[JobResponse]
    count: int


class ProgramResponse(BaseModel):
    """Metadata of a program."""

    name: str
    cost: Optional[int] = 600
    description: str
    version: Optional[str] = "1.0"
    backendRequirements: Optional[dict] = None
    parameters: Optional[List[dict]] = None
    returnValues: Optional[List[dict]] = None
    isPublic: Optional[bool] = True


class ProgramsResponse(BaseModel):
    """Metadata of all programs."""

    programs: List[ProgramResponse]


@runtime.post("/jobs", summary="Run a program", tags=["jobs"])
def run_job(program_call: ProgramParams):
    """Run a quantum program"""
    program_id = program_call.programId
    metadata = load_metadata(program_id)
    kwargs = json.loads(program_call.params[0], cls=RuntimeDecoder) if program_call.params else {}
    job = Job.create(
        launch,
        args=(program_id, _DEFAULT_SIMULATOR, kwargs),
        result_ttl=-1,
        failure_ttl=-1,
        timeout=metadata["max_execution_time"],
        connection=redis_client,
    )
    job.meta["log_path"] = get_job_log_path(job.id)
    job.meta["result_path"] = get_job_result_path(job.id)
    job.meta["channel_id"] = get_job_channel_id(job.id)
    job.save_meta()
    queue.enqueue_job(job)
    return {"id": job.id}


@runtime.get("/jobs", summary="List jobs", response_model=JobsResponse, tags=["jobs"])
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
    """List my quantum program jobs"""
    job_status = _pending_status() if pending else _finished_status()
    all_job_ids = (
        queue.get_job_ids() + started.get_job_ids()
        if pending
        else finished.get_job_ids() + failed.get_job_ids()
    )
    runtime_jobs = [_to_job_response(queue.fetch_job(job_id)) for job_id in all_job_ids]
    filtered_jobs = [job for job in runtime_jobs if job.status in job_status]

    jobs = filtered_jobs[offset : offset + limit]
    count = len(jobs)

    return JobsResponse(jobs=jobs, count=count)


@runtime.get(
    "/jobs/{job_id}", summary="Get a program job", response_model=JobResponse, tags=["jobs"]
)
def get_job(job_id: str):
    """Get a program job"""
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return _to_job_response(job)


@runtime.get("/jobs/{job_id}/logs", summary="List job logs", tags=["jobs"])
def get_job_logs(job_id: str):
    """List all job logs"""
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    with open(job.meta["log_path"], "r") as log_file:
        return log_file.read()


@runtime.get("/jobs/{job_id}/results", summary="List job results", tags=["jobs"])
def get_job_results(job_id: str):
    """List all job results"""
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        with open(job.meta["result_path"], "r") as result_file:
            return result_file.read()
    except OSError:
        return ""


@runtime.delete(
    "/jobs/{job_id}", summary="Deletes a job", status_code=status.HTTP_204_NO_CONTENT, tags=["jobs"]
)
def delete_job(job_id: str):
    """Delete the specified job"""
    job = queue.fetch_job(job_id)
    if job:
        completed_job_ids = finished.get_job_ids() + failed.get_job_ids()
        if job_id in completed_job_ids:
            job.delete()
            return

        raise HTTPException(status_code=403, detail="Job not finalized")

    raise HTTPException(status_code=404, detail="Job not found")


@runtime.post(
    "/jobs/{job_id}/cancel",
    summary="Cancels the job execution",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["jobs"],
)
def cancel_job(job_id: str):
    """
    The real Qiskit Runtime can cancel the job execution but this is **not**
    supported in the test server.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Job not finalized. The test server cannot cancel jobs.",
    )


@runtime.get("/stream/jobs/{job_id}", summary="Websocket: get the job result stream", tags=["jobs"])
def stream_job_results_docs(_):
    """
    Get a job results stream as the job runs
    """
    pass


@runtime.websocket("/stream/jobs/{job_id}")
async def stream_job_results(job_id: str, websocket: WebSocket):
    """Sends logs and results via websocket."""
    job = queue.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await websocket.accept()
    redis_conn = redis_client.connection_pool.get_connection("_")
    async_client = aioredis.Redis(host=redis_conn.host, port=redis_conn.port, db=redis_conn.db)

    async with async_client.pubsub() as pubsub:
        channel_id = job.meta["channel_id"]
        await pubsub.subscribe(channel_id)

        is_result = False
        while not is_result:
            message = await pubsub.get_message()
            if message and message["type"] == "message":
                is_result, message_text = _parse_message(message)
                # TODO: should we treat the message differently if it is a result?
                await websocket.send_text(message_text)

        await pubsub.unsubscribe(channel_id)

    await websocket.close()


@runtime.get(
    "/programs",
    summary="List programs",
    response_model=ProgramsResponse,
    tags=["programs"],
)
def get_programs():
    """List all of my programs"""
    all_program_ids = all_programs()
    all_metadata = [_to_program_response(program_id) for program_id in all_program_ids]
    return ProgramsResponse(programs=all_metadata)


@runtime.get(
    "/programs/{program_id}",
    summary="Show the info of a program",
    response_model=ProgramResponse,
    tags=["programs"],
)
def get_program(program_id: str):
    """Show the info of the specified program."""
    module_path = resolve_program_module_path(program_id)
    if not module_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

    return _to_program_response(program_id)


def _to_job_response(job):
    program_id, backend, kwargs = job.args
    return JobResponse(
        id=job.id,
        hub="test-hub",
        group="test-group",
        project="test-project",
        backend=backend,
        status=_STATUS_MAP[job.get_status()],
        params=[json.dumps(kwargs)],
        program=program_id,
        created=job.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    )


def _to_program_response(program_id):
    metadata = load_metadata(program_id)
    return ProgramResponse(**metadata)


def _pending_status():
    return list(map(_STATUS_MAP.get, ["queued", "started"]))


def _finished_status():
    return list(map(_STATUS_MAP.get, ["finished", "stopped", "failed"]))


def _parse_message(message):
    redis_message = message["data"].decode("utf-8")
    message_type, message_text = redis_message.split(":", 1)
    return message_type == "result", message_text
