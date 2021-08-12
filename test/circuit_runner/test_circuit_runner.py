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

"""Test the circuit runner program."""

from qiskit.providers.ibmq import RunnerResult
from qiskit import IBMQ, QuantumCircuit
from unittest import TestCase
from qiskit.providers.jobstatus import JobStatus

class TestCircuitRunner(TestCase):
    """Test circuit_runner."""

    def setUp(self) -> None:
        """Test case setup."""
        self.provider = IBMQ.load_account()
        N = 6
        qc = QuantumCircuit(N)
        qc.x(range(0, N))
        qc.h(range(0, N))
        self.qc = qc
        
    def test_circuit_runner(self):
        """Test circuit_runner program."""
        program_inputs = {
            'circuits': self.qc,
            'shots': 2048,
            'optimization_level': 0,
            'initial_layout': [0,1,4,7,10,12],
            'measurement_error_mitigation': False
        }

        options = {'backend_name': "ibmq_qasm_simulator"}

        job = self.provider.runtime.run(program_id="circuit-runner",
                                    options=options,
                                    inputs=program_inputs,
                                    result_decoder=RunnerResult
                                    )
        result = job.result()
        self.assertEqual(str(job.status()), JobStatus.DONE)

