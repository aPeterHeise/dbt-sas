#!/usr/bin/env python
#
# Copyright (c) 2022, Alkemy Spa and/or its affiliates.
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

__all__ = [
    "DEFAULT_PORT",
    "DEFAULT_DB",
    "LIBNAME_MAX_LEN",
    "DATA_SET_MAX_LEN",
    "DEFAULT_HANDLER",
    "DEFAULT_WS_USER",
    "DEFAULT_WS_PASSWORD",
    "DEFAULT_WS_URL",
    "WORK_SCHEMA",
    "DUMMY_FROM",
    "DEFAULT_CTE_SCHEMA",
]

# Default SAS port
DEFAULT_PORT = 8591
# Default database name
DEFAULT_DB = "sas"
# Max library name length
LIBNAME_MAX_LEN = 8
# Max data set name length
DATA_SET_MAX_LEN = 32
# Handle
DEFAULT_HANDLER = "ws"  # "saspy"
# Default web service handler username
DEFAULT_WS_USER = "sasjdbc"
# Default web service handler password
DEFAULT_WS_PASSWORD = "sasjdbc"
# Default web service handler url
DEFAULT_WS_URL = "http://localhost:8099"
# Schema for the temp view (CTE)
DEFAULT_CTE_SCHEMA = "cte"
# Work schema
WORK_SCHEMA = "work"
# Dummy from when from table is missing
DUMMY_FROM = """
from sashelp.vdctnry
where memname='DICTIONARIES' and name='NAME'
"""
