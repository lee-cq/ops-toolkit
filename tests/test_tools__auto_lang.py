#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_tools__auto_lang.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 21:37
"""
from translate.tools import auto_lang


def test_auto_lang():
    test_str = {
        ("简体中文", "cn"),
        ("English", "en"),
        ("繁體中文", "tw"),
        ("!@#$%^&*()", "en"),
        ("123456", "en"),
        ("中文English", "en"),
        ("Hello 你好", "en"),
    }
    for s, r in test_str:
        assert auto_lang(s) == r, f"{s} 识别为 {auto_lang(s)}，而不是 {r}"
