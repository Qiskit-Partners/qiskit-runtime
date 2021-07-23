"""Loads Qiskit Runtime metadata."""

import os
import json


def load_metadata(program_module_path):
    program_module_filesystem_path = _to_filesystem_path_without_extension(program_module_path)
    location, name = os.path.split(program_module_filesystem_path)
    metadata_name = f"{name}.json"
    metadata_path = os.path.join(location, metadata_name)
    with open(metadata_path, "r") as fd:
        return json.load(fd)


def _to_filesystem_path_without_extension(program_module_path: str):
    return os.path.join(os.path.curdir, program_module_path.replace(".", "/"))
