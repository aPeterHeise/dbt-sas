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

import pkgutil
import jinja2


__all__ = [
    "NOOP",
    "PROC_SQL",
    "PROC_SQL_SELECT",
    "DELETE_FILE",
    "RENAME_DATA_SET",
    "DELETE_DATA_SET",
    "TRUNCATE_DATA_SET",
    "IMPORT_CSV",
    "ASSIGN_LIBNAMES",
    "CREATE_SCHEMA",
    "DROP_SCHEMA",
    "COLUMNS_EQUAL",
    "UPLOAD_FILE",
]


def load_sas(filename: str) -> jinja2.Template:
    template: str = pkgutil.get_data(__name__, filename).decode("utf-8")
    return jinja2.Template(template)


NOOP = load_sas("code/noop.sas")
PROC_SQL = load_sas("code/proc_sql.sas")
PROC_SQL_SELECT = load_sas("code/proc_sql_select.sas")
DELETE_FILE = load_sas("code/delete_file.sas")
RENAME_DATA_SET = load_sas("code/rename_data_set.sas")
DELETE_DATA_SET = load_sas("code/delete_data_set.sas")
TRUNCATE_DATA_SET = load_sas("code/truncate_data_set.sas")
IMPORT_CSV = load_sas("code/import_csv.sas")
ASSIGN_LIBNAMES = load_sas("code/assign_libnames.sas")
CREATE_SCHEMA = load_sas("code/create_schema.sas")
DROP_SCHEMA = load_sas("code/drop_schema.sas")
COLUMNS_EQUAL = load_sas("code/columns_equal.sql")
UPLOAD_FILE = load_sas("code/upload_file.sas")
