#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_translate_show.py
@Author     : LeeCQ
@Date-Time  : 2025/9/20 13:26
"""
import tkinter
import unittest

from ops_toolkit.translate.ui_window_translate import TranslationWindow


class TestApp:

    def __init__(self):
        self.root = tkinter.Tk()
        self.root.withdraw()  # 隐藏主窗口


class TestTranslationWindow(unittest.TestCase):

    def setUp(self):
        self.app = TestApp()
        self.window = TranslationWindow(self.app)

    def test_show(self):
        self.window.show(
            "aaa", "啊"
        )
        self.app.root.mainloop()
