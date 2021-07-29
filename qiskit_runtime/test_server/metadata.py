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

"""Loads Qiskit Runtime metadata."""

import os
import pathlib
import configparser
import json
from functools import wraps

_CONFIG = configparser.ConfigParser()
_CONFIG_FILE_PATH = pathlib.Path(os.path.join(os.path.dirname(__file__), "config.ini"))
_LAST_MODIFICATION_TIME = 0
_METADATA_DEFAULTS = {"max_execution_time": 300}


def _ensure_latest_configfile(target):
    @wraps(target)
    def _wrapped(*args, **kwargs):
        # pylint: disable=global-statement
        global _CONFIG
        global _LAST_MODIFICATION_TIME
        # pylint: enable=global-statement
        current_modification_time = _CONFIG_FILE_PATH.stat().st_mtime
        if current_modification_time > _LAST_MODIFICATION_TIME:
            _LAST_MODIFICATION_TIME = current_modification_time
            _CONFIG = configparser.ConfigParser()
            _CONFIG.read(_CONFIG_FILE_PATH)

        return target(*args, **kwargs)

    return _wrapped


@_ensure_latest_configfile
def resolve_program_module_path(program_id):
    """Get the path to the program entry point."""
    return _CONFIG.get("programs", program_id)


@_ensure_latest_configfile
def all_programs():
    """Return a list of all program ids."""
    return [program_name for program_name, _ in _CONFIG.items("programs")]


def load_metadata(program_id):
    """Loads the metadata for a program."""
    program_module_path = resolve_program_module_path(program_id)
    program_module_filesystem_path = _to_filepath_without_extension(program_module_path)
    location, name = os.path.split(program_module_filesystem_path)
    metadata_name = f"{name}.json"
    metadata_path = os.path.join(location, metadata_name)
    with open(metadata_path, "r") as fd:
        metadata = json.load(fd)
        metadata_with_defaults = {**_METADATA_DEFAULTS, **metadata}
        return metadata_with_defaults


def _to_filepath_without_extension(program_module_path: str):
    return os.path.join(os.path.curdir, program_module_path.replace(".", "/"))
