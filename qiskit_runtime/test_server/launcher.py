import importlib


def launch(program_module_path, simulator_name, kwargs):
    program_module = importlib.import_module(program_module_path)
    from qiskit import Aer
    from qiskit.providers.ibmq.runtime import UserMessenger

    backend = Aer.get_backend(simulator_name)
    user_messenger = UserMessenger()
    program_module.main(backend, user_messenger, **kwargs)
