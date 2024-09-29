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

from dataclasses import dataclass
from typing import Optional, Tuple

from dbt.adapters.base import Credentials
from dbt.adapters.sas.constants import (
    DEFAULT_CTE_SCHEMA,
    DEFAULT_DB,
    DEFAULT_HANDLER,
    DEFAULT_PORT,
    DEFAULT_WS_PASSWORD,
    DEFAULT_WS_URL,
    DEFAULT_WS_USER,
)

__all__ = ["SasCredentials"]


@dataclass(init=False)
class SasCredentials(Credentials):
    """Connect to SAS via Java IOM"""

    # IOM user
    username: str
    # Password for the IOM user
    password: str
    # Libname
    schema: str
    # Host name, or ip to the IOM server to connect to
    host: str
    # Port IOM is listening on
    port: int = DEFAULT_PORT
    # Path to the java executable
    java_path: Optional[str] = None
    # Timeout value for establishing connection to workspace server
    timeout: Optional[int] = None
    # Autoexec
    autoexec: Optional[str] = None
    # Libraries base path
    lib_base_path: Optional[str] = None
    # Strict mode
    lib_name_strict_mode: bool = False
    # Raise and error if it encounters a warning
    fail_on_warnings: bool = True
    # Schema for the temp view (CTE)
    cte_schema: str = DEFAULT_CTE_SCHEMA
    # Ignored
    database: str = DEFAULT_DB
    # Handler
    handler: str = DEFAULT_HANDLER
    # Web service handler username
    ws_basic_user: str = DEFAULT_WS_USER
    # Web service handler password
    ws_basic_password: str = DEFAULT_WS_PASSWORD
    # Web service handler url
    ws_base_url: str = DEFAULT_WS_URL

    _ALIASES = {
        "pass": "password",
        "user": "username",
        "lib": "schema",
    }

    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.database = DEFAULT_DB

    @property
    def type(self) -> str:
        """Return name of adapter."""
        return "sas"

    @property
    def unique_field(self) -> str:
        """
        Hashed and included in anonymous telemetry to track adapter adoption.
        Pick a field that can uniquely identify one team/organization building with this adapter
        """
        return self.host

    def _connection_keys(self) -> Tuple[str]:
        """
        List of keys to display in the `dbt debug` output.
        """
        return ("host", "port", "username", "schema")
