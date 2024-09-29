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

import base64
import tempfile
import uuid
from pathlib import Path
from typing import Any, List

import agate

from dbt.adapters.sas.constants import WORK_SCHEMA
from dbt.exceptions import RuntimeException

__all__ = [
    "get_temp_filename",
    "get_temp_local_filename",
    "get_temp_data_set_name",
    "path_join",
    "agate_table_get_column_values",
]


def get_temp_filename(ext: str = "") -> str:
    """Create a temporary filename"""
    return f"/tmp/{str(uuid.uuid4())}{ext}"


def get_temp_local_filename(ext: str = "") -> Path:
    """Create a temporary local filename"""
    return Path(tempfile.gettempdir()) / f"{str(uuid.uuid4())}{ext}"


def get_temp_data_set_name(schema: str = WORK_SCHEMA) -> str:
    """Create a temporary data set name"""
    # The data set name can be up to 32 bytes long for the Base SAS engine starting in Version 7
    uuid_bytes = uuid.uuid4().bytes
    table_name = base64.b32encode(uuid_bytes).decode("ascii").replace("=", "")[:20]
    return f"{schema}.TMP_{table_name}"


def path_join(*parts: List[str]) -> str:
    """Join two or more pathname components"""
    parts = [x for x in parts if x]
    if not parts:
        return ""
    if any([x for x in parts if ".." in x]):
        raise RuntimeException("Invalid path")
    # Count posix separators
    p1 = len([x for x in parts if x.startswith("/") or x.endswith("/")])
    p2 = len([x for x in parts if "/" in x])
    # Count windows separators
    w1 = len([x for x in parts if x.endswith("\\")])
    w2 = len([x for x in parts if "\\" in x])
    if w1 > p1 or w2 > p2:
        separator = "\\"  # Windows separator
    else:
        separator = "/"  # Posix sepatator
    result = separator.join([x.strip(separator) for x in parts if x])
    if separator == "/" and not result.startswith("/") and parts[0].startswith("/"):
        result = "/" + result
    return result


def agate_table_get_column_values(table: agate.Table, column: str) -> List[Any]:
    """Retun the values from an agate.Table's column"""
    col = table.columns.get(column)
    if col is None:
        return []
    else:
        return col.values()
