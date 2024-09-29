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
import struct
import zlib
from dataclasses import dataclass
from typing import Optional, TypeVar

from dbt.adapters.base.relation import BaseRelation, Policy
from dbt.adapters.sas.connections import is_lib_name_strict_mode
from dbt.adapters.sas.constants import DATA_SET_MAX_LEN, DEFAULT_DB, LIBNAME_MAX_LEN
from dbt.contracts.relation import RelationType
from dbt.exceptions import DatabaseException

__all__ = [
    "SasRelation",
    "is_valid_libname",
    "get_short_libname",
]

Self = TypeVar("Self", bound="SasRelation")


@dataclass
class SasQuotePolicy(Policy):
    database: bool = False
    schema: bool = False
    identifier: bool = False


@dataclass
class SasIncludePolicy(Policy):
    database: bool = False  # exclude "database" part from idenfifier
    schema: bool = True
    identifier: bool = True


@dataclass(frozen=True, eq=False, repr=False)
class SasRelation(BaseRelation):
    quote_policy: SasQuotePolicy = SasQuotePolicy()
    include_policy: SasIncludePolicy = SasIncludePolicy()
    quote_character: str = ""

    @property
    def libname(self):
        return self.schema.upper()

    @property
    def dataset(self):
        return self.identifier.upper()

    def include(
        self,
        database: Optional[bool] = None,
        schema: Optional[bool] = None,
        identifier: Optional[bool] = None,
    ) -> Self:
        return super().include(database=False, schema=schema, identifier=identifier)

    @classmethod
    def create(
        cls,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        identifier: Optional[str] = None,
        type: Optional[RelationType] = None,
        **kwargs,
    ) -> Self:
        if is_lib_name_strict_mode():
            if schema:
                schema = schema.lower()
                for prefix in ("dbt_test_dbt_test_", "dbt_test_"):
                    if schema.startswith(prefix):
                        schema = schema[len(prefix) :].strip('_')
                        schema = f"t_{schema}"
                if len(schema) > LIBNAME_MAX_LEN:
                    raise DatabaseException(f"`{schema}` is not a valid libname (length > {LIBNAME_MAX_LEN})")
            if identifier and len(identifier) > DATA_SET_MAX_LEN:
                raise DatabaseException(f"`{identifier}` is not a valid data set name (length > {DATA_SET_MAX_LEN}")
        else:
            if schema:
                schema = schema.lower()
                if not is_valid_libname(schema):
                    schema = get_short_libname(schema)
            if identifier:
                identifier = identifier[:DATA_SET_MAX_LEN]
        return super().create(database=DEFAULT_DB, schema=schema, identifier=identifier, type=type, **kwargs)

    @staticmethod
    def add_ephemeral_prefix(name: str) -> str:
        return f"_cte_{name}"


def is_valid_libname(libname: str) -> bool:
    if libname.lower() == "dictionary":
        return True
    else:
        return len(libname) <= LIBNAME_MAX_LEN


def get_short_libname(libname: str) -> str:
    "Compute the short (8 chars) libname from a long libname"
    if is_valid_libname(libname):
        return libname.lower()
    else:
        crc = zlib.crc32(libname.lower().encode('ascii'))
        return "_" + base64.b32encode(struct.pack('I', crc)).decode('ascii').strip('=')[:7]
