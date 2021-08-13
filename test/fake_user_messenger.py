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

import json
from qiskit.providers.ibmq.runtime.utils import RuntimeEncoder
from typing import Any, Type

class FakeUserMessenger:
    def __init__(self):
        self.call_count = 0
        self.message = None

    def publish(self, message: Any, \
        encoder: Type[json.JSONEncoder] = RuntimeEncoder, \
        final: bool = False
        ):
        self.message = message
        self.call_count += 1
        