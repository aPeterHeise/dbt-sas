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

from dataclasses import dataclass
from typing import TypeVar

from dbt.adapters.base.column import Column
from dbt.exceptions import RuntimeException

__all__ = ["SasColumn", "TEXT"]

Self = TypeVar("Self", bound="SasColumn")

# SAS Data types:
# CHAR, CHARACTER, DATE, DEC, DECIMAL, DOUBLE, FLOAT, INT, INTEGER,
# NUM, NUMERIC, REAL, SMALLINT, VARCHAR
# https://support.sas.com/documentation/cdl/en/fedsqlref/67364/HTML/default/viewer.htm#n19bf2z7e9p646n0z224cokuj567.htm


TEXT_SIZE = 32767
TEXT = f"VARCHAR({TEXT_SIZE})"
STRING_DATATYPES = {"char", "character", "varchar", "nchar", "nvarchar"}
INTEGER_DATATYPES = {"int", "integer", "smallint", "tinyint"}
FLOAT_DATATYPES = {"dec", "decimal", "double", "float", "num", "numeric", "real", "smallint"}
NUMBER_DATATYPES = set()
NUMBER_DATATYPES.update(INTEGER_DATATYPES)
NUMBER_DATATYPES.update(FLOAT_DATATYPES)


@dataclass(init=False)
class SasColumn(Column):
    TYPE_LABELS = {
        "STRING": TEXT,
        "TIMESTAMP": "DATE",
        "FLOAT": "FLOAT",
        "INTEGER": "INTEGER",
        "BOOLEAN": "SMALLINT",
    }

    STRING_DATATYPES = STRING_DATATYPES
    INTEGER_DATATYPES = INTEGER_DATATYPES
    FLOAT_DATATYPES = FLOAT_DATATYPES
    NUMBER_DATATYPES = NUMBER_DATATYPES

    def string_size(self) -> int:
        if not self.is_string():
            raise RuntimeException("Called string_size() on non-string field!")
        if self.dtype == "text" or self.char_size is None:
            return TEXT_SIZE
        else:
            return int(self.char_size)

    @property
    def data_type(self) -> str:
        if self.is_string():
            return self.string_type(self.string_size())
        elif self.is_numeric():
            return self.numeric_type(self.dtype, self.numeric_precision, self.numeric_scale)
        else:
            return self.dtype

    @classmethod
    def string_type(cls, size: int) -> str:
        return "varchar({})".format(size)

    def is_float(self) -> bool:
        return self.dtype.lower() in self.FLOAT_DATATYPES

    def is_integer(self) -> bool:
        return self.dtype.lower() in self.INTEGER_DATATYPES

    def is_numeric(self) -> bool:
        return self.dtype.lower() in self.NUMBER_DATATYPES

    def is_string(self) -> bool:
        return self.dtype.lower() in self.STRING_DATATYPES
