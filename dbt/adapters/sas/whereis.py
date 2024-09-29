#!/usr/bin/env python
#
# Copyright (c) 2022, Alkemy Spa
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import platform
from pathlib import Path
from typing import Optional

IS_WINDOWS = platform.system() == "Windows"
PATH_SEPARATOR = ";" if IS_WINDOWS else ":"

DEFAULT_PATH = [
    "/usr/bin",
    "/usr/sbin",
    "/bin",
    "/sbin",
    "/lib",
    "/lib32",
    "/lib64",
    "/usr/local/bin",
    "/usr/local/sbin",
    "/usr/local/lib",
    "/usr/contrib",
    "/usr/hosts",
]

__all__ = ["whereis"]


def whereis(name: str) -> Optional[Path]:
    """Locate the binary for a command"""
    if not name:
        return None
    if IS_WINDOWS:
        name = name + ".exe"
    for path in os.environ.get("PATH", "").split(PATH_SEPARATOR) or DEFAULT_PATH:
        path = Path(path) / name
        if path.exists():
            return path
    return None
