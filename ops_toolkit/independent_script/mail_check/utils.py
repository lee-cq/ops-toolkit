#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : utils
@Author     : LeeCQ
@Date-Time  : 2026/8/17 


"""
import logging
import os
from pathlib import Path

logger = logging.getLogger("mail-check.utils")

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.name.endswith(".pyz"):
    SCRIPT_DIR = SCRIPT_DIR.parent
    os.chdir(SCRIPT_DIR)


def load_env(file=None):
    """"""
    if file:
        logger.info(f"LOAD ENV: {file}")
        for line in Path(file).read_text(encoding="utf8").splitlines():
            line = line.strip("\n").strip("\r")
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            logger.debug(f"SET ENV SUCCESS: {k}: {'*' * (len(v))}{v[-2:]}")
            os.environ[k] = v.strip('"').strip("'")
        return

    logger.debug(f"DIR: {Path(__file__).parents[::-1]}")
    for _ in Path(__file__).parents[::-1]:
        if _.joinpath(".env").is_file():
            logger.debug("LOAD ENV FROM: {}")
            load_env(file=_.joinpath(".env"))
