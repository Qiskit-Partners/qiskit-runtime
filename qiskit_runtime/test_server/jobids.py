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
