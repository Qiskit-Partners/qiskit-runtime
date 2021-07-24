import os


def get_job_channel_id(job_id):
    return f"job-results:{job_id}"


def get_job_log_path(job_id):
    return get_log_file(f"{job_id}.log")


def get_job_result_path(job_id):
    return get_log_file(f"{job_id}.result.log")


def get_log_file(filename):
    logdir = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(__file__)
            ),
        ),
        "logs"
    )
    if not os.path.exists(logdir):
        os.mkdir(logdir)
    return os.path.join(logdir, filename)
