#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_tray.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:13
"""
from pathlib import Path

import pystray
from PIL import Image


class SystemTray:
    def __init__(self, app):
        self.app = app
        self.icon = None

        # 创建托盘图标
        self.create_icon()

    def create_icon(self):
        """创建系统托盘图标"""
        # 创建一个简单的图标
        image = Image.open(Path(__file__).parent.joinpath("resources/app-icon.png.py").open("rb"))

        # 创建菜单
        menu = pystray.Menu(
            pystray.MenuItem("翻译记录", self.show_history),
            pystray.MenuItem("词汇分析", self.show_word_analysis),
            pystray.MenuItem("运行日志", self.show_logs),
            pystray.MenuItem("设置", self.show_settings),
            pystray.MenuItem("退出", self.exit_app)
        )

        # 创建图标
        self.icon = pystray.Icon(self.app.config.app_name, image, self.app.config.app_name, menu)

    def run(self):
        """运行托盘图标"""
        if self.icon:
            self.icon.run()

    def show_history(self, icon, item):
        """显示翻译历史"""
        self.app.root.after(0, self.app.show_history_window)

    def show_word_analysis(self, icon, item):
        """显示词汇分析"""
        self.app.root.after(0, self.app.show_word_analysis_window)

    def show_logs(self, icon, item):
        """显示运行日志"""
        self.app.root.after(0, self.app.show_log_window)

    def show_settings(self, icon, item):
        """显示设置窗口"""
        self.app.root.after(0, self.app.show_settings_window)

    def exit_app(self, icon, item):
        """退出应用程序"""
        self.icon.stop()
        self.app.root.after(0, self.app.quit)
