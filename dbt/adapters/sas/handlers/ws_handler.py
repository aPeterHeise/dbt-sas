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

import json
from typing import List, Optional

import agate
import requests
from requests.exceptions import RequestException

from dbt.adapters.sas import sas_log
from dbt.adapters.sas.credentials import SasCredentials
from dbt_common.clients.agate_helper import DEFAULT_TYPE_TESTER
from dbt_common.exceptions import DbtDatabaseError, ConnectionError

from .abstract_handler import AbstractConnectionHandler

__all__ = ["WsConnectionHandler"]

SessionId = str


class WsConnectionHandler(AbstractConnectionHandler):
    """Connect to SAS via Web Service"""

    def __init__(self, credentials: SasCredentials) -> None:
        super().__init__(credentials)

    def submit(self, code: str, note: Optional[str] = None, ignore_warnings: bool = False) -> str:
        """Submit code to the SAS server"""
        return self._submit(code, session_id=self.get_session_id(), note=note, ignore_warnings=ignore_warnings)

    def _submit(self, code: str, session_id: SessionId, note: Optional[str] = None, ignore_warnings: bool = False) -> str:
        if note:
            sas_log.note(note)
        sas_log.debug(code, family="sas")
        params = {"sessionId": session_id}
        data = json.dumps(
            {
                "code": code,
            }
        )
        response = self.request(path="rsubmit/rs", method="POST", params=params, data=data).json()
        self.check_error(response["output"], ignore_warnings=ignore_warnings)
        return response["output"]

    def select(self, sql: str) -> agate.Table:
        """Execute a SQL select on the SAS server"""
        return self._select(sql, session_id=self.get_session_id())

    def _select(self, sql: str, session_id: SessionId) -> agate.Table:
        params = {"sessionId": session_id, "size": 100000}
        sql = sql.rstrip(";")
        data = json.dumps(
            {
                "query": sql,
            }
        )
        response = self.request(path="sql/select", method="POST", params=params, data=data).json()
        # if sas_log.enabled:
        #    sas_log.debug(str(response), family="sql")
        return agate.Table.from_object(response["results"], column_types=DEFAULT_TYPE_TESTER)

    def endsas(self) -> None:
        """Terminate the SAS session, shutting down the SAS process"""
        pass  # TODO

    def url(self, path: str) -> str:
        """Return the full web service url"""
        return f"{self.credentials.ws_base_url}/{path}"

    def request(self, path: str, method: str = "GET", **kargs):
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        try:
            response = requests.request(
                method=method,
                url=self.url(path),
                auth=(self.credentials.ws_basic_user, self.credentials.ws_basic_password),
                headers=headers,
                **kargs,
            )
        except RequestException as ex:
            raise DbtDatabaseError(str(ex))
        if response.status_code == 401:
            raise DbtDatabaseError("Invalid Web Service credentials")
        if response.status_code != 200:
            try:
                message = response.json()["error"]
            except Exception:
                message = response.text
            sas_log.error(message)
            raise DbtDatabaseError(message)
        return response

    def list_sessions(self) -> List[SessionId]:
        """List sessions"""
        return self.request(method="GET", path="session").json().get("sessions", [])

    def open_session(self) -> SessionId:
        """Open a new session and return the session id"""
        path = f"session/user/{self.credentials.username}"
        params = {
            "password": self.credentials.password,
            "host": self.credentials.host,
            "port": self.credentials.port,
        }
        response = self.request(method="GET", path=path, params=params).json()
        if response["status"] != "success":
            raise DbtDatabaseError("Error opening SAS session")
        session_id = response.get("session").get("sessionId")
        # Load autoexec
        autoexec = self.load_autoexec(self.credentials)
        if autoexec:
            output = self._submit(autoexec, session_id=session_id)
            sas_log.debug(output, family="sas")
        return session_id

    def get_session_id(self) -> SessionId:
        """Get the session id of an already existing session or open a new session"""
        try:
            sessions = [
                x
                for x in self.list_sessions()
                if x.get("username") == self.credentials.username
                and x.get("host") == self.credentials.host
                and x.get("port") == self.credentials.port
            ]
            if sessions:
                return sessions[0].get("sessionId")
            else:
                return self.open_session()
        except DbtDatabaseError as ex:
            raise ConnectionError(ex.msg)
