#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : version.py
@Author     : LeeCQ
@Date-Time  : 2025/10/14 22:23
"""


def get_version():
    _main_split = UPDATE_LOG.strip().split('\n\n')[0].split('\n')
    _m, _fix_log = _main_split[0], _main_split[-1]
    return f"{_m}.{_fix_log.split('.')[0]}"


UPDATE_LOG = """
1.1
1. 添加ROW REQUEST日志方便分析Translate API的原始记录
2. 防止调整translate窗口时的无限递归
3. 更新版本号生成机制
4. 优化自动识别语言逻辑，移除tw因为基本用不到，现在繁体在识别和翻译前将直接转换为简体 #20 #22

1.0.0
"""

VERSION = get_version()

if __name__ == '__main__':
    print(get_version())
