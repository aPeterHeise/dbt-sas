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

import abc
from pathlib import Path
from typing import Optional

import agate

from dbt.adapters.sas import sas_log, sas_macros
from dbt.adapters.sas.credentials import SasCredentials
from dbt_common.exceptions import (
    DbtRuntimeError
)
from dbt.adapters.sas.utils import path_join


__all__ = ["AbstractConnectionHandler"]


class AbstractConnectionHandler(abc.ABC):
    def __init__(self, credentials: SasCredentials) -> None:
        self.credentials = credentials

    @abc.abstractmethod
    def submit(self, code: str, note: Optional[str] = None) -> str:
        """Submit code to the SAS server"""
        return NotImplemented

    @abc.abstractmethod
    def select(self, sql: str) -> agate.Table:
        """Execute a SQL select on the SAS server"""
        return NotImplemented

    @abc.abstractmethod
    def endsas(self) -> None:
        """Terminate the SAS session, shutting down the SAS process"""
        return NotImplemented

    def upload_file(self, local_filename: str, remote_filename: str) -> None:
        """Upload a file to the SAS server"""
        data = Path(local_filename).read_text().rstrip("\n")
        code = sas_macros.UPLOAD_FILE.render(remote_filename=remote_filename, data=data)
        self.submit(code, note="sas")

    def delete_file(self, remote_filename: str) -> None:
        """Delete a file from the SAS server"""
        sas_log.note(f"Delete file - Filename={remote_filename}")
        code = sas_macros.DELETE_FILE.render(remote_filename=remote_filename)
        self.submit(code)

    def check_error(self, output: str, ignore_warnings: bool = False):
        """Check for error message in the result log"""
        log_lines = output.splitlines()
        if self.credentials.fail_on_warnings and not ignore_warnings:
            error_lines = [line for line in log_lines if line.startswith("ERROR") or line.startswith("WARNING")]
        else:
            error_lines = [line for line in log_lines if line.startswith("ERROR")]
        if error_lines:
            sas_log.error(output)
            raise DbtRuntimeError(error_lines[0])

    @classmethod
    def load_autoexec(self, credentials: SasCredentials) -> str:
        # Load autoexec
        if credentials.autoexec:
            autoexec = Path(credentials.autoexec).read_text()
        else:
            autoexec = ""
        # Create CTE schema
        if credentials.cte_schema and credentials.lib_base_path:
            path = path_join(credentials.lib_base_path, credentials.cte_schema.lower())
            autoexec += "\n\n"
            autoexec += sas_macros.CREATE_SCHEMA.render(libname=credentials.cte_schema.lower(), path=path)
        # Append auto assign libname to autoexec
        if credentials.lib_base_path:
            autoexec += "\n\n"
            autoexec += sas_macros.ASSIGN_LIBNAMES.render(path=credentials.lib_base_path)
        return autoexec
