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

__all__ = "get_handler"

from typing import Type

from dbt.exceptions import RuntimeException

from .abstract_handler import AbstractConnectionHandler


def get_handler(handler: str) -> Type[AbstractConnectionHandler]:
    if handler == "ws":
        from .ws_handler import WsConnectionHandler

        return WsConnectionHandler
    elif handler == "saspy":
        from .saspy_handler import SaspyConnectionHandler

        return SaspyConnectionHandler
    else:
        raise RuntimeException(f"Invalid handle f{handler}")
