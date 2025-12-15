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
    return f"{_m.strip()}.{_fix_log.split('.')[0]}"


UPDATE_LOG = """
1.3 
1. 更改baidu翻译API接口为aiTextTranslate
2. 新增clipboard_monitor.py，用于监听剪切板内容变化
3. 新增clipboard窗口，用于展示剪切板内容
4. 新增开机自启配置项
5. 修复开机自启配置错误的程序路径

1.2
1. 添加translate-cli
2. 添加other_tools.keepalive.py，用于保持电脑活跃
3. 添加other_tools.hourly_reminder.py，用于每小时提醒
4. fix: zhconv导入失败
5. fix: json依赖未被包含
6. 优化:pytray MENU 的更新逻辑
7. hourly_reminder支持在最长4小时后开始提醒
8. config.py Config.Feishu 添加空默认值，确认无配置启动

1.1
1. 添加ROW REQUEST日志方便分析Translate API的原始记录
2. 防止调整translate窗口时的无限递归
3. 更新版本号生成机制
4. api_abs 中添加Response使用字符串提示类型
5. 优化自动识别语言逻辑，移除tw因为基本用不到，现在繁体在识别和翻译前将直接转换为简体 #20 #22
6. 因开发者不再维护zhconv，将zhconv内联到项目中，自维护，基于1.4.4版本

1.0.0
"""

VERSION = get_version()

if __name__ == '__main__':
    print(get_version())
