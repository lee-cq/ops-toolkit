#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : version.py
@Author     : LeeCQ
@Date-Time  : 2025/10/14 22:23
"""
from pathlib import Path

DEBUGGER = Path(__file__).parent.parent.joinpath("README.md").exists()


def get_version():
    if DEBUGGER:
        readme = Path(__file__).parent.parent.joinpath("README.md")
        other_line = readme.read_text(encoding="utf-8").split("## CHANGELOG")[0]
        readme.write_text(other_line + UPDATE_LOG.strip(), encoding="utf-8")

    _main_split = UPDATE_LOG.strip().split("## CHANGELOG")[1].strip().split('\n\n')[0].split('\n')
    _m, _fix_log = _main_split[0], _main_split[-1]
    return f"{_m.strip()}.{_fix_log.split('.')[0]}".replace('###', '').strip()


UPDATE_LOG = """
## CHANGELOG

### 1.7
1. 添加自动更新功能
2. 修复重构项目结构时的遗留问题
3. add: 锁屏检查 fix: teams检查遇到的任何问题跳过本次检查

### 1.6
1. 移除飞书相关代码
2. 重构项目文件结构
3. 添加cnb CI配置
4. 优化通知提示，添加app_id
5. 优化坐标选择器，先截图在创建窗口，避免在创建窗口后内容变更，保证获得的坐标准确
6. 优化坐标选择器，选择完成后先清空原来的内容
7. 修复开机自启配置错误
8. 修复teams notify找不到app_id
9. 修复keepalive在某些情况下失效的问题

### 1.5
1. 新增teams通知监控
2. 变更CHANGELOG位置到README.md
3. 更新依赖
4. trams监控添加了配置项
5. trams监控添加了GUI日志
6. 完善README.md，添加使用说明

### 1.4
1. 新增aliyun_sls_split.py，用于切割阿里云日志下载文件
2. 新增UI到托盘，打开下载窗口
3. 新增自动识别aliyun SLS链接，自动弹出窗口
4. 优化Hostname的处理，移除域名
5. 单一文件中添加source, path, content三列，用|||分隔
6. 优化ui_window_sls_split.py，打开工作目录选择默认值

### 1.3
1. 更改baidu翻译API接口为aiTextTranslate
2. 新增clipboard_monitor.py，用于监听剪切板内容变化
3. 新增clipboard窗口，用于展示剪切板内容
4. 新增开机自启配置项
5. 修复开机自启配置错误的程序路径

### 1.2
1. 添加translate-cli
2. 添加other_tools.keepalive.py，用于保持电脑活跃
3. 添加other_tools.hourly_reminder.py，用于每小时提醒
4. fix: zhconv导入失败
5. fix: json依赖未被包含
6. 优化:pytray MENU 的更新逻辑
7. hourly_reminder支持在最长4小时后开始提醒

### 1.1
1. 添加ROW REQUEST日志方便分析Translate API的原始记录
2. 防止调整translate窗口时的无限递归
3. 更新版本号生成机制
4. api_abs 中添加Response使用字符串提示类型
5. 优化自动识别语言逻辑，移除tw因为基本用不到，现在繁体在识别和翻译前将直接转换为简体 #20 #22
6. 因开发者不再维护zhconv，将zhconv内联到项目中，自维护，基于1.4.4版本

### 1.0.0
"""

VERSION = get_version()

if __name__ == '__main__':
    print(f"Version: {get_version()}")
    print(f"DEBUGGER: {DEBUGGER}")
