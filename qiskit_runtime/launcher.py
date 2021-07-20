import importlib

PROGRAM_MAP = {
    'circuit-runner': 'qiskit_runtime.circuit_runner.circuit_runner',
    'qka': 'qiskit_runtime.qka.qka',
    'vqe': 'qiskit_runtime.vqe.vqe',
    'sample-program': 'qiskit_runtime.sample_program.sample_program'
}

def launch(program_id, simulator_name, kwargs):
    program_module_path = PROGRAM_MAP[program_id]
    program_module = importlib.import_module(program_module_path)
    from qiskit import Aer
    from qiskit.providers.ibmq.runtime import UserMessenger
    backend = Aer.get_backend(simulator_name)
    user_messenger = UserMessenger()
    program_module.main(backend, user_messenger, **kwargs)