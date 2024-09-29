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

import itertools
from typing import Any, List, Optional, Tuple

import agate

from dbt.adapters.base import BaseAdapter, available
from dbt.adapters.base.relation import BaseRelation
from dbt.adapters.sas import SasConnectionManager, sas_log, sas_macros
from dbt.adapters.sas.column import TEXT, SasColumn
from dbt.adapters.sas.constants import DEFAULT_DB
from dbt.adapters.sas.relation import SasRelation
from dbt.adapters.sas.utils import (
    agate_table_get_column_values,
    get_temp_filename,
    get_temp_local_filename,
    path_join,
)
from dbt.contracts.graph.manifest import Manifest
from dbt.adapters.contracts.relation import RelationType
from dbt_common.exceptions import DbtRuntimeError

__all__ = ["SasAdapter"]


class SasAdapter(BaseAdapter):
    ConnectionManager = SasConnectionManager
    Relation = SasRelation
    Column = SasColumn

    """
    Methods:
        - exception_handler
        - date_function
        - list_schemas [OK]
        - drop_relation [OK]
        - truncate_relation [OK]
        - rename_relation [OK]
        - get_columns_in_relation [OK] - TODO: check data types
        - expand_column_types
        - list_relations_without_caching [OK]
        - is_cancelable [OK]
        - create_schema [OK]
        - drop_schema [OK]
        - quote [OK]
        - convert_text_type
        - convert_number_type
        - convert_boolean_type [OK]
        - convert_datetime_type
        - convert_date_type
        - convert_time_type
        - standardize_grants_dict

    Macros:
        - get_catalog
    """

    @classmethod
    def date_function(cls):
        """
        Returns canonical date func
        """
        return "datetime()"  # format=datetime22.

    def debug_query(self) -> None:
        sas_log.note("Debug query")
        connection = self.connections.get_thread_connection()
        connection.handle.submit(sas_macros.NOOP.render())

    @classmethod
    def is_cancelable(cls) -> bool:
        return False

    def list_schemas(self, database: str) -> List[str]:
        """Get a list of existing libraries"""
        table = self.execute_macro("list_schemas", kwargs={"database": ""})
        return agate_table_get_column_values(table, "libname")

    def list_relations_without_caching(self, schema_relation: BaseRelation) -> List[BaseRelation]:
        """List data sets in the given library, bypassing the cache."""
        table = self.execute_macro("list_relations_without_caching", kwargs={"schema_relation": schema_relation})
        tables = agate_table_get_column_values(table, "memname")
        types = agate_table_get_column_values(table, "type")
        return [
            SasRelation.create(database=DEFAULT_DB, schema=schema_relation.libname, identifier=identifier, type=RelationType(type_))
            for (identifier, type_) in zip(tables, types)
        ]

    def run_sql_for_tests(self, sql, fetch: str, conn):
        """This method is used by the test suite"""
        _, result = self.execute(sql, fetch=fetch in ("one", "all"))
        if fetch == "one":
            return result[0]
        elif fetch == "all":
            return list(result)
        else:
            return

    @classmethod
    def convert_text_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return TEXT

    @classmethod
    def convert_number_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))  # type: ignore[attr-defined]
        return "float" if decimals else "integer"

    @classmethod
    def convert_boolean_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return "int"

    @classmethod
    def convert_datetime_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return "date"  # TODO

    @classmethod
    def convert_date_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return "date"  # TODO

    @classmethod
    def convert_time_type(cls, agate_table: agate.Table, col_idx: int) -> str:
        return "date"  # TODO

    @available
    def should_identifier_be_quoted(self, identifier, models_column_dict=None) -> bool:
        """Returns True if identifier should be quoted else False"""
        return False

    @available
    def check_and_quote_identifier(self, identifier, models_column_dict=None) -> str:
        return identifier

    @classmethod
    def quote(cls, identifier: str) -> str:
        return identifier

    def create_schema(self, relation: SasRelation) -> None:
        """Create a new library in the lib_base_path directory"""
        sas_log.note(f"Create schema {relation}")
        connection = self.connections.get_thread_connection()
        lib_base_path = connection.credentials.lib_base_path
        if not lib_base_path:
            raise DbtRuntimeError(
                "`lib_base_path` option is required for schema creation - please add the option to the profiles.yml configuration"
            )
        path = path_join(lib_base_path, relation.libname.lower())
        connection.handle.submit(sas_macros.CREATE_SCHEMA.render(libname=relation.libname, path=path))

    def drop_schema(self, relation: SasRelation) -> None:
        sas_log.note(f"Drop schema {relation}")
        connection = self.connections.get_thread_connection()
        lib_base_path = connection.credentials.lib_base_path
        if not lib_base_path:
            raise DbtRuntimeError(
                "`lib_base_path` option is required for dropping schemas - please add the option to the profiles.yml configuration"
            )
        path = path_join(lib_base_path, relation.libname.lower())
        connection.handle.submit(sas_macros.DROP_SCHEMA.render(libname=relation.libname, path=path), ignore_warnings=True)
        self.cache.drop_schema(relation.database, relation.schema)

    def truncate_relation(self, relation: SasRelation) -> None:
        sas_log.note(f"Truncate relation {relation}")
        connection = self.connections.get_thread_connection()
        connection.handle.submit(
            sas_macros.TRUNCATE_DATA_SET.render(
                libname=relation.libname,
                dataset=relation.dataset,
            )
        )

    def rename_relation(self, from_relation: SasRelation, to_relation: SasRelation) -> None:
        sas_log.note(f"Rename relation {from_relation} -> {to_relation}")
        connection = self.connections.get_thread_connection()
        connection.handle.submit(
            sas_macros.RENAME_DATA_SET.render(
                libname=from_relation.libname, old_name=from_relation.dataset, new_name=to_relation.dataset
            )
        )

    def drop_relation(self, relation: SasRelation):
        sas_log.note(f"Drop relation {relation}")
        connection = self.connections.get_thread_connection()
        connection.handle.submit(
            sas_macros.DELETE_DATA_SET.render(
                libname=relation.libname,
                dataset=relation.dataset,
            )
        )

    def get_columns_in_relation(self, relation: SasRelation) -> List[SasColumn]:
        """Get a list of the columns in the given Relation."""
        sas_log.note(f"Get columns in relation {relation}")
        table = self.execute_macro("sas__get_columns_in_relation", kwargs={"relation": relation})
        names = agate_table_get_column_values(table, "name")
        types = agate_table_get_column_values(table, "type")
        lengths = agate_table_get_column_values(table, "length")
        return [
            SasColumn(name, type_, length) for (name, type_, length) in zip(names, types, lengths)
        ]  # TODO check data types (data types are 'num' and 'char')

    def get_relation(self, database: str, schema: str, identifier: str) -> Optional[BaseRelation]:
        return super().get_relation(DEFAULT_DB, schema, identifier)  # Force default db

    def expand_column_types(self, goal: SasRelation, current: SasRelation) -> None:  # type: ignore[override]
        pass

    def expand_target_column_types(self, from_relation: SasRelation, to_relation: SasRelation) -> None:
        pass

    @available
    def import_seed(
        self,
        agate_table: agate.Table,
        relation: SasRelation,
    ) -> Tuple[Any, Any]:
        """Import seed into the SAS server

        1) Store data from an agate table into a CSV file
        2) Upload the CSV file to the SAS server
        3) Import the data into target table (relation)
        4) Delete the local/remote temp files
        """
        connection = self.connections.get_thread_connection()
        local_filename = get_temp_local_filename(ext=".csv")
        remote_filename = get_temp_filename(ext=".csv")
        try:
            # Save the data in a local CSV file
            agate_table.to_csv(local_filename, delimiter=",")  # TODO: check quoted
            # Upload the CSV to the SAS server
            connection.handle.upload_file(local_filename, remote_filename)
            # Import the CSV into the target table
            sas_log.note(f"Import CSV from {remote_filename} into {relation.libname}.{relation.dataset}")
            code = sas_macros.IMPORT_CSV.render(
                libname=relation.libname,
                dataset=relation.dataset,
                filename=remote_filename,
            )
            connection.handle.submit(code)
            sas_log.note("CSV Import done")
            return code
        finally:
            # Delete the local file
            try:
                local_filename.unlink()
            except Exception:
                pass
            # Delete the file from the SAS server
            try:
                sas_log.note(f"Delete file - Filename={remote_filename}")
                code = sas_macros.DELETE_FILE.render(remote_filename=remote_filename)
                connection.handle.submit(code)
            except Exception:
                pass

    # This method only really exists for test reasons.
    def get_rows_different_sql(
        self,
        relation_a: SasRelation,
        relation_b: SasRelation,
        column_names: Optional[List[str]] = None,
        except_operator: str = "EXCEPT",
    ) -> str:
        """Generate SQL for a query that returns a single row with a two
        columns: the number of rows that are different between the two
        relations and the number of mismatched rows.
        """
        names: List[str]
        if column_names is None:
            columns = self.get_columns_in_relation(relation_a)
            names = sorted((c.name for c in columns))
        else:
            names = sorted((n for n in column_names))
        columns_csv = ", ".join(names)
        return sas_macros.COLUMNS_EQUAL.render(
            columns=columns_csv,
            relation_a=relation_a.render(),
            relation_b=relation_b.render(),
            except_op=except_operator,
        )

    @available
    def verify_database(self, database: str) -> str:
        # return an empty string on success so macros can call this
        return ""

    def get_catalog(self, manifest: Manifest) -> Tuple[agate.Table, List[Exception]]:
        for node in itertools.chain(manifest.nodes.values(), manifest.sources.values()):
            node.database = DEFAULT_DB  # Force default db
        return super().get_catalog(manifest)
