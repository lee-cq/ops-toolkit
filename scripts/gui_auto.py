#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : gui_auto.py
@Author     : LeeCQ
@Date-Time  : 2026/1/23 08:21
"""
import typing

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App


def gui_auto(self: "App"):
    self.root.after(1000, self.settings_window.show)
