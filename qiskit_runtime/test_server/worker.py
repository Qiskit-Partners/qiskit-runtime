#!/usr/bin/env python

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
