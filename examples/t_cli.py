#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : t_cli.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:23
"""
import os

os.environ["TRANSLATE_CONFIG_PATH"] = "_lo_config.toml"


from translate.app import TranslationApp

app = TranslationApp()
app.run()
