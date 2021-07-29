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

"""
Utilities for generating names, identifiers, paths... per jobs.
"""

import os


def get_job_channel_id(job_id):
    """Generate a name for identifying the channel in which publish program results."""
    return f"job-results:{job_id}"


def get_job_log_path(job_id):
    """Generate the path for the log file."""
    return get_log_file(f"{job_id}.log")


def get_job_result_path(job_id):
    """Generate the path for the result file."""
    return get_log_file(f"{job_id}.result.log")


def get_log_file(filename):
    """Generate a log file in the log folder."""
    logdir = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(__file__)),
        ),
        "logs",
    )
    if not os.path.exists(logdir):
        os.mkdir(logdir)
    return os.path.join(logdir, filename)
