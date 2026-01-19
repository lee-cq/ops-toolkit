#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_tools__auto_lang.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 21:37
"""
from ops_toolkit.tools import auto_lang


def test_auto_lang():
    test_str = (
        ("简体中文", "zh"),
        ("English", "en"),
        ("繁體中文", "zh"),
        ("!@#$%^&*()", "en"),
        ("123456", "en"),
        ("Hello 你好", "zh"),
        ("误报", 'zh'),
        ("JunhongAPP无法获取行情信息", "zh"),
        ("sms-service-log日志接收可能异常：", "zh"),
        ("logs 是否需要收集到EMP", "zh"),
        ("今天 01-02，请求HSBC API时发生21次503/500错误", "zh"),
    )
    for s, r in test_str:
        assert auto_lang(s) == r, f"{s} 识别为 {auto_lang(s)}，而不是 {r}, code: {",".join(f'{ord(_):04x}' for _ in s)}"
