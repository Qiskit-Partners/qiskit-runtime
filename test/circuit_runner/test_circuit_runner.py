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

# import sys, os
# sys.path.insert(0, os.path.join(os.getcwd(), "../../qiskit_runtime"))

from qiskit.providers.aer import AerSimulator
from qiskit_runtime.circuit_runner import circuit_runner
from qiskit import QuantumCircuit
from test.fake_user_messenger import FakeUserMessenger
from unittest import TestCase

class TestCircuitRunner(TestCase):
    """Test circuit_runner."""

    def setUp(self) -> None:
        """Test case setup."""
        N = 6
        qc = QuantumCircuit(N)
        qc.x(range(0, N))
        qc.h(range(0, N))
        self.qc = qc
        self.backend = AerSimulator()
        self.user_messenger = FakeUserMessenger()
        
    def test_circuit_runner(self):
        """Test circuit_runner program."""
        circuit_runner.main(backend=self.backend, user_messenger=self.user_messenger, \
            circuits=self.qc, optimization_level=0, \
            initial_layout=[0,1,4,7,10,12], \
            measurement_error_mitigation=False)
        self.assertEqual(self.user_messenger.call_count, 1)
