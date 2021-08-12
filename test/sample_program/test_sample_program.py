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

"""Test the sample_program."""
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "../../qiskit_runtime"))

from qiskit_runtime.sample_program import sample_program
from qiskit import Aer
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder, RuntimeDecoder
from qiskit.providers.ibmq.runtime import UserMessenger
from unittest import TestCase
import json
class TestSampleProgram(TestCase):
    """Test sample_program."""
    def test_run_program(self):
        """Test sample program."""
        input = {
            "iterations": 2
        }
        backend = Aer.get_backend('aer_simulator')
        user_messenger = UserMessenger()
        serialized_inputs = json.dumps(input, cls=RuntimeEncoder)
        unserialized_inputs = json.loads(serialized_inputs, cls=RuntimeDecoder)
        sample_program.main(backend, user_messenger, **unserialized_inputs)
