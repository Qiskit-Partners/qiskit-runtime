#!/usr/bin/env python

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

"""The worker in charge of running the Qiskit Runtime programs."""

import os
import sys
from rq import Connection, Worker

# Preload libraries
# pylint: disable=unused-import
import qiskit
import qiskit_nature

# pylint: enable=unused-import

# Look for modules in the directory from which the worker is run
sys.path.insert(0, os.getcwd())

# Provide queue names to listen to as arguments to this script,
# similar to rq worker
with Connection():
    qs = sys.argv[1:] or ["default"]

    w = Worker(qs)
    w.work()
