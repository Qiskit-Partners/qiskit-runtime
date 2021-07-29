"""Prepare the environment (the runtime) for launching Qiskit Runtime programs."""

import json
import importlib
from typing import Any, Type
from contextlib import ExitStack, redirect_stdout, redirect_stderr

from qiskit.providers.ibmq.runtime import UserMessenger
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder

from rq import get_current_job, get_current_connection


class TestServerUserMessenger(UserMessenger):
    """
    A messenger for redirecting executions logs to a file and streaming communications
    back to the test server through Redis.

    Must be used within a `with` block, the return value of the `with` block will be the
    messanger itself.

    All messages are sent back to the test sever through Redis, and all standard output,
    errors and final result are also persistend in disk.
    """

    def __init__(self):
        job = get_current_job()
        self._log_file = job.meta["log_path"]
        self._result_path = job.meta["result_path"]
        self._channel_id = job.meta["channel_id"]
        self._connection = get_current_connection()
        self._exit_stack = ExitStack()
        self._context_started = False

    def __enter__(self):
        self._log_file = open(self._log_file, "w")
        self._exit_stack.enter_context(self._log_file)
        self._exit_stack.enter_context(redirect_stdout(self._log_file))
        self._exit_stack.enter_context(redirect_stderr(self._log_file))
        self._context_started = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def publish(
        self, message: Any, encoder: Type[json.JSONEncoder] = RuntimeEncoder, final: bool = False
    ) -> None:
        if not self._context_started:
            raise RuntimeError("`TestServerUserMessenger` cannot be used outside of a context.")

        text_message = json.dumps(message, cls=encoder)

        self._publish_on_stdout(text_message, final)
        self._publish_on_redis(text_message, final)
        if final:
            self._publish_result_on_disk(text_message)

    def _publish_on_stdout(self, message: str, _: bool) -> None:
        """Print the message on stdout."""
        print(message)

    def _publish_on_redis(self, message: str, final: bool) -> None:
        """Publish the message on Redis."""
        message_type = "result" if final else "interim"
        redis_message = f"{message_type}:{message}"
        redis_payload = redis_message.encode("utf-8")
        self._connection.publish(self._channel_id, redis_payload)

    def _publish_result_on_disk(self, message: str) -> None:
        """Log the message on log and result files."""
        with open(self._result_path, "w") as result_file:
            result_file.write(message)


def launch(program_module_path, simulator_name, kwargs):
    """Prepare and launch the Qiskit Runtime program."""

    with TestServerUserMessenger() as user_messenger:
        from qiskit import Aer

        program_module = importlib.import_module(program_module_path)
        backend = Aer.get_backend(simulator_name)

        program_module.main(backend, user_messenger, **kwargs)
