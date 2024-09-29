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

from contextlib import contextmanager
from typing import ContextManager, Tuple

import agate

from dbt.adapters.base import BaseConnectionManager
from dbt.adapters.sas import sas_log, sas_macros
from dbt.adapters.sas.credentials import SasCredentials
from dbt.adapters.sas.cte import prepare_query
from dbt.adapters.sas.handlers import get_handler
from dbt.contracts.connection import AdapterResponse, Connection, ConnectionState
from dbt_common.exceptions import (
    DbtRuntimeError,
    ConnectionError
)
from dbt.logger import GLOBAL_LOGGER as logger

__all__ = [
    "SasConnectionManager",
    "is_lib_name_strict_mode",
]


default_credentials: SasCredentials = SasCredentials()


def is_lib_name_strict_mode() -> bool:
    "Lib name strict mode"
    return default_credentials.lib_name_strict_mode


class SasConnectionManager(BaseConnectionManager):
    TYPE = "sas"

    @contextmanager
    def exception_handler(self, sql: str) -> ContextManager:
        try:
            yield
        except Exception as ex:
            logger.debug(f"Error while running:\n{sql}")
            logger.debug(ex)
            raise DbtRuntimeError(str(ex))

    @classmethod
    def open(cls, connection: Connection) -> Connection:
        """Connect to SAS"""
        global default_credentials
        if connection.state == ConnectionState.OPEN:
            logger.debug("Connection is already open, skipping open.")
            return connection
        else:
            try:
                # Open Connection
                handle_class = get_handler(connection.credentials.handler)
                connection.handle = handle_class(connection.credentials)
                connection.state = ConnectionState.OPEN
                default_credentials = connection.credentials
                return connection
            except ConnectionError:
                connection.handle = None
                connection.state = ConnectionState.FAIL
                raise

    @classmethod
    def close(cls, connection: Connection) -> Connection:
        """Close connection."""
        if connection.state in {ConnectionState.CLOSED, ConnectionState.INIT}:
            return connection
        else:
            try:
                connection.state = ConnectionState.CLOSED
                connection.handle.endsas()
                connection.handle = None
            except Exception:
                pass
            finally:
                return connection

    def begin(self) -> None:
        """Begin a transaction."""
        pass

    def commit(self) -> None:
        """Commit a transaction."""
        pass

    def clear_transaction(self) -> None:
        """Clear any existing transactions."""
        pass

    def cancel_open(self) -> None:
        """Cancel all open connections on the adapter."""
        pass

    @classmethod
    def get_response(cls, message: str) -> AdapterResponse:
        return AdapterResponse(_message=message)

    def execute(self, sql: str, auto_begin: bool = False, fetch: bool = False) -> Tuple[AdapterResponse, agate.Table]:
        """Execute the given SQL.

        :param str sql: The SQL to execute.
        :param bool auto_begin: Ignored.
        :param bool fetch: If set, fetch results.
        :return: A tuple of the query status and results (empty if fetch=False).
        :rtype: Tuple[AdapterResponse, agate.Table]
        """
        sas_log.note(f"Execute SQL, fetch: {fetch}")
        connection = self.get_thread_connection()
        if fetch and not sql.strip().lower().startswith("select"):
            sas_log.note("Not a select, set fetch to False")
            fetch = False
        if fetch:
            table = self.select(connection, sql)
            message = "SELECT"
        else:
            table = self.proc_sql(connection, sql)
            message = "OK"
        return (self.get_response(message), table)

    def proc_sql(self, connection: Connection, sql: str) -> agate.Table:
        """Execute and SQL Procedure - it does not fetch the result and returns and empty table"""
        sas_log.debug(f"Original SQL: {sql}", family="original_sql")
        query = prepare_query(sql, cte_schema=connection.credentials.cte_schema)
        # Create temp tables
        if query.pre:
            sas_log.debug(f"Pre SQL statement: {query.pre}", family="sql")
            code = sas_macros.PROC_SQL.render(sql=query.pre)
            if query.ctes:
                delete_data_sets_code = sas_macros.DELETE_DATA_SET.render(
                    libname=connection.credentials.cte_schema,
                    dataset=query.ctes.keys(),
                )
                code = f"{delete_data_sets_code}\n{code}"
            connection.handle.submit(code)
        # Query
        sas_log.debug(f"SQL statement: {query.query}", family="sql")
        code = sas_macros.PROC_SQL.render(sql=query.query)
        connection.handle.submit(code)
        # Drop temp tables
        if query.post:
            sas_log.debug(f"Post SQL statements: {query.post}", family="sql")
            code = sas_macros.PROC_SQL.render(sql=query.post)
            connection.handle.submit(code)
        return agate.Table(rows=[])

    def select(self, connection: Connection, sql: str) -> agate.Table:
        """Execute a SQL select on the SAS server"""
        sas_log.debug(f"Original SQL: {sql}", family="original_sql")
        query = prepare_query(sql, cte_schema=connection.credentials.cte_schema)
        # Create temp tables
        if query.pre:
            sas_log.debug(f"Pre SQL statement: {query.pre}", family="sql")
            code = sas_macros.PROC_SQL.render(sql=query.pre)
            connection.handle.submit(code)
        # Query
        sas_log.debug(f"SQL statement: {query.query}", family="sql")
        result = connection.handle.select(query.query)
        # Drop temp tables
        if query.post:
            sas_log.debug(f"Post SQL statements: {query.post}", family="sql")
            code = sas_macros.PROC_SQL.render(sql=query.post)
            connection.handle.submit(code)
        return result

    def delete_file(self, connection: Connection, remote_filename: str) -> None:
        """Delete a file from the SAS server"""
        connection.handle.delete_file(remote_filename)
