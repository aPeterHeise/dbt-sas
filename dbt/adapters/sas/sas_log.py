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

import logging
import os
from pathlib import Path
from typing import Optional, Set, Tuple

__all__ = [
    "note",
    "debug",
    "info",
    "warn",
    "warning",
    "error",
    "critical",
    "fatal",
    "enabled",
]


def prepare_logger() -> Tuple[logging.Logger, bool, Set[str]]:
    logger = logging.getLogger("sas-dbt")
    dbt_sas_log = os.environ.get("DBT_SAS_LOG")
    families = set([x.lower() for x in os.environ.get("DBT_SAS_FAMILY", "sql").split(",")])
    if not dbt_sas_log:
        logger.setLevel(logging.ERROR)
        enabled = False
    else:
        log_file = Path(dbt_sas_log)
        if log_file.exists() and not os.environ.get("DBT_SAS_KEEP_LOG"):
            log_file.unlink()
        logger.setLevel(logging.DEBUG)
        f_handler = logging.FileHandler(dbt_sas_log)
        f_format = logging.Formatter("%(message)s")
        # f_format = logging.Formatter("%(asctime)s %(message)s")
        f_handler.setFormatter(f_format)
        logger.addHandler(f_handler)
        enabled = True
    return logger, enabled, families


def is_enabled(family: Optional[str]) -> bool:
    return enabled and ((not family) or (family in families))


def note(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"NOTE: {msg}"
        logger.debug(msg, *args, **kargs)


def debug(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"\n{msg}\n"
        logger.debug(msg, *args, **kargs)


def info(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"INFO: {msg}"
        logger.info(msg, *args, **kargs)


def warn(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"WARNING: {msg}"
        logger.warn(msg, *args, **kargs)


def warning(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"WARNING: {msg}"
        logger.warning(msg, *args, **kargs)


def error(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"ERROR: {msg}"
        logger.error(msg, *args, **kargs)


def critical(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"CRITICAL: {msg}"
        logger.critical(msg, *args, **kargs)


def fatal(msg, family: Optional[str] = None, *args, **kargs) -> None:
    if is_enabled(family):
        msg = f"FATAL: {msg}"
        logger.fatal(msg, *args, **kargs)


logger, enabled, families = prepare_logger()
