#!/usr/bin/en
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

import json
import os
import time
from io import BytesIO
from typing import Optional

import agate
import saspy
from saspy.sasexceptions import SASIOConnectionError

from dbt.adapters.sas import sas_log, sas_macros
from dbt.adapters.sas.credentials import SasCredentials
from dbt.adapters.sas.utils import get_temp_data_set_name, get_temp_filename
from dbt.adapters.sas.whereis import whereis
from dbt_common.clients.agate_helper import DEFAULT_TYPE_TESTER
from dbt_common.exceptions import (
    DbtRuntimeError,
    ConnectionError,
    DbtConfigError
)
from dbt.logger import GLOBAL_LOGGER as logger

from .abstract_handler import AbstractConnectionHandler

__all__ = ["SaspyConnectionHandler"]


class SaspyConnectionHandler(AbstractConnectionHandler):
    def __init__(self, credentials: SasCredentials) -> None:
        super().__init__(credentials)
        # Load autoexec
        autoexec = self.load_autoexec(credentials)
        # Search for java
        java = credentials.java_path or whereis("java")
        if not java:
            raise ConnectionError("Java not found in path.")
        # Open SAS session
        try:
            self.session = saspy.SASsession(
                java=str(java),
                iomhost=credentials.host,
                iomport=credentials.port,
                omruser=credentials.username,
                omrpw=credentials.password,
                timeout=credentials.timeout,
                autoexec=autoexec or None,
            )
        except SASIOConnectionError as ex:
            logger.debug(f"Got an error when attempting to create SAS Session: '{ex}'")
            raise ConnectionError(str(ex))

    def submit(self, code: str, note: Optional[str] = None, ignore_warnings: bool = False) -> str:
        """Submit code to the SAS server"""
        if note:
            sas_log.note(note)
        sas_log.debug(code, family="sas")
        result = self.session.submit(code, "text")
        self.check_error(result["LOG"], ignore_warnings=ignore_warnings)
        return result["LOG"]

    def select(self, sql: str) -> agate.Table:
        """Execute a SQL select on the SAS server"""
        temp_table = get_temp_data_set_name()
        temp_filename = get_temp_filename()
        sas_log.note(f"Execute select and save output to file - Filename={temp_filename}")
        sas_log.debug(sql, family="sql")
        code = sas_macros.PROC_SQL_SELECT.render(sql=sql, temp_table=temp_table, temp_filename=temp_filename)
        try:
            # Execute the query and save results as JSON
            self.submit(code)
            # Download response ad JSON
            return self.download_json(temp_filename, family="sql")
        finally:
            # Delete the temp file from the SAS server
            self.delete_file(temp_filename)

    def endsas(self) -> None:
        """Terminate the SAS session, shutting down the SAS process"""
        self.session.endsas()

    def download_file(self, filename: str, family: Optional[str] = None) -> BytesIO:
        """This method downloads a file from the SAS servers file system"""
        sas_log.note(f"Download Filename={filename}")
        logn = self.session._io._logcnt()
        logcodeb = f"\nE3969440A681A24088859985{logn}".encode()

        valid = self.session._io._sb.file_info(filename, quiet=True)
        if valid is None:
            raise DbtRuntimeError(f"{filename} not found")
        elif valid == {}:
            raise DbtRuntimeError(f"{filename} is a directory")

        code = f"filename _sp_updn '{filename}' recfm=F encoding=binary lrecl=4096;"
        self.session._io.submit(code, "text")
        self.session._io.stdin[0].send(b"tom says EOL=DNLOAD                          \n")
        self.session._io.stdin[0].send(b"\ntom says EOL=" + logcodeb + b"\n")

        done = False
        data = b""
        bail = False
        output = BytesIO()
        while not done:
            if os.name == "nt":
                try:
                    rc = self.session._io.pid.wait(0)
                    self.session._io.pid = None
                    self.session._io._sb.SASpid = None
                    raise DbtRuntimeError("SAS process has terminated unexpectedly")
                except DbtRuntimeError:
                    raise
                except Exception:
                    pass
            else:
                rc = os.waitpid(self.session._io.pid, os.WNOHANG)
                if rc[1]:
                    self.session._io.pid = None
                    self.session._io._sb.SASpid = None
                    raise DbtRuntimeError("SAS process has terminated unexpectedly")

            if bail:
                if logcodeb in data:
                    done = True
                    break
            try:
                data = self.session._io.stdout[0].recv(4096)
                if logcodeb in data:
                    data = data.rpartition(logcodeb)[0]
                    done = True
                output.write(data)
            except BlockingIOError:
                data = b""

            if not data:
                time.sleep(0.1)
                try:
                    log = self.session._io.stderr[0].recv(4096)
                except BlockingIOError:
                    log = b""
                if logcodeb in log:
                    bail = True

        if sas_log.enabled:
            output.seek(0, 0)  # rewind
            sas_log.debug(output.getvalue().decode("utf-8"), family=family)

        output.seek(0, 0)  # rewind
        return output

    def download_json(self, filename: str, family: Optional[str]) -> agate.Table:
        """Download an parse a JSON file from the SAS servers file system"""
        try:
            file_content = self.download_file(filename, family=family)
            data = json.load(file_content)
            return agate.Table.from_object(data, column_types=DEFAULT_TYPE_TESTER)
        except json.decoder.JSONDecodeError as ex:
            sas_log.error(f"Error parsing JSON response: {str(ex)}")
            raise DbtConfigError(f"Error parsing JSON response: {str(ex)}")
