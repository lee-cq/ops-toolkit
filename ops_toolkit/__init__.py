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
### 1.8
1. 添加aliyun-sls-sdk下载功能
2. fix:添加aliyun-log-python-sdk依赖
3. 添加todolist task
4. update_version 支持选择beta版本
5. [todolist] add "删除任务" 优化 窗口布局
6. [update_version] fix 更新提醒和beta提示
7. [todolist] add "到期提醒功能" update "history 表结构"
8. [todolist] add "取消提醒" add "添加提醒的任务添加标记 #30 " op "延时体验"
9. [todolist] add "添加任务编辑功能 #31 "
10. [todolist] add "工作目录管理 #33 " op "悬停标题时显示详细信息"
11. [update_version] fix "无法退出CMD"
12. [app] op "使用typer优化命令行体验" fix "配置文件序列化错误" fix ""
13. [hourly_reminder] add "延迟提醒功能"
14. [todolist] fix "文件管理重复创建目录" op "界面展示"
15b1. [app] op "重构翻译在App中的位置" op "优化退出机制和定时器机制" 
15. [15b1]
16b1. [todolist] add "添加task管理窗口"
16b3. [todolist] add "Remake #34 " op "Create 窗口描述使用长文本框"
16b4. [todolist] fix "无法更新状态" op "status 和 str 的关系"
16b5. [app] op "每小时自动检查更新"
16. [15b1, 16b1, 16b3, 16b4, 16b5]
17b1. [todolist] add "按班次周期任务提醒 #35 " op "记忆浮窗位置 #37 "
17b2. [todolist] op "ToolTip 显示位置，防止溢出屏幕 #36 "
17b3. [todolist] fix "管理窗口，工时展示错误 #39 "
17b4. [hourly_reminder] fix "通知界面格式化字符串异常"
17b5. [todolist.models] op "DB.update_task 通知逻辑优化"
17b6. [todolist.scheduler] fix "编码错误" op "调整默认值"
17b7. [todolist.reminder] op "延时的通知"
17b8. [update_version] fix "升级脚本"
17b9. [todolist.model] op "重构session"
17b10. [todolist.scheduler] fix "通知回调错误"
17b11. [todolist.TaskItem] fix "延迟时间后通知未更新reminder"  fix [17b10]
17. [17b1, 17b2, 17b3, 17b4, 17b5, 17b6, 17b7, 17b8, 17b9, 17b10, 17b11]
18. [todolist] op 窗口延时更新 op "异步初始化" op "添加日志" op "添加上班下班的触发函数" op "右键更新窗口"
19. [update_version] op "更新完成后5秒自动重启"
20. [todolist] fix "浮窗界面右键菜单失效" op "优化提醒逻辑"
21b1. [todolist.scheduler] fix 超时后无法更新计划

### 1.7
1. 添加自动更新功能
2. 修复重构项目结构时的遗留问题
3. add: 锁屏检查 fix: teams检查遇到的任何问题跳过本次检查
4. fix: 在有屏幕缩放的系统中调用屏幕选择器异常，更新脚本提前终止
5. fix: teams监控更新截图未设置超时时间
6. fix: teams监控第N+1次打开后无法正常显示截图预览
7. fix: update_version 版本统一变量

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
