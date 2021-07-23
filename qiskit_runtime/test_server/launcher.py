import importlib
from contextlib import redirect_stderr, redirect_stdout

from rq import get_current_job


def launch(program_module_path, simulator_name, kwargs):
    program_module = importlib.import_module(program_module_path)
    from qiskit import Aer
    from qiskit.providers.ibmq.runtime import UserMessenger

    backend = Aer.get_backend(simulator_name)
    user_messenger = UserMessenger()
    job = get_current_job()
    log_path = job.meta["log_path"]
    with open(log_path, "w") as log_file:
        with redirect_stdout(log_file), redirect_stderr(log_file):
            program_module.main(backend, user_messenger, **kwargs)
