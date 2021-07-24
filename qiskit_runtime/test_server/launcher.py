"""Prepare the environment (the runtime) for launching Qiskit Runtime programs."""

import json
import importlib
from qiskit_runtime.test_server.ioutils import get_job_channel_id
from typing import Any, Type
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder


from rq import get_current_job, get_current_connection
from qiskit.providers.ibmq.runtime import UserMessenger


class TestServerUserMessenger(UserMessenger):
    """
    A messenger for sending communications back to the test server through redis.

    All messages are sent back to the test sever through Redis, and the final result
    is also persisted in disk.
    """

    def publish(
        self, message: Any, encoder: Type[json.JSONEncoder] = RuntimeEncoder, final: bool = False
    ) -> None:
        text_message = json.dumps(message, cls=encoder)
        print(text_message)

        job_id = get_current_job().id
        redis_conn = get_current_connection()
        redis_conn.publish(get_job_channel_id(job_id), text_message)

        if final:
            job = get_current_job()
            result_path = job.meta["result_path"]
            with open(result_path, "w") as result_file:
                result_file.write(text_message)


def launch(program_module_path, simulator_name, kwargs):
    """Prepare and launch the Qiskit Runtime program."""

    with redirect_output_to_log_file():
        from qiskit import Aer

        program_module = importlib.import_module(program_module_path)
        user_messenger = TestServerUserMessenger()
        backend = Aer.get_backend(simulator_name)

        program_module.main(backend, user_messenger, **kwargs)


@contextmanager
def redirect_output_to_log_file():
    """Redirect stdout and stderr to the job log file."""

    job = get_current_job()
    log_path = job.meta["log_path"]
    with open(log_path, "w") as log_file:
        with redirect_stdout(log_file), redirect_stderr(log_file):
            yield
