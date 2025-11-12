#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_tray.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:13
"""
import logging
import threading
import time
from pathlib import Path

import pystray
from PIL import Image

logger = logging.getLogger("translate.app_tray")


class SystemTray:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.update_thread: threading.Thread | None = None

        # 创建托盘图标
        self.create_icon()

    def create_icon(self):
        """创建系统托盘图标"""
        # 创建一个简单的图标
        image = Image.open(Path(__file__).parent.joinpath("resources/app-icon.png.py").open("rb"))
        # 创建图标
        self.icon = pystray.Icon(
            self.app.config.app_name, image, self.app.config.app_name, pystray.Menu(
                pystray.MenuItem("翻译记录", self.show_history),
                pystray.MenuItem("运行日志", self.show_logs),
                pystray.MenuItem(
                    lambda _ic: f"保持活跃({self.app.keepalive.is_running()}): {self.app.keepalive.ctrl_press_count}",
                    self.keepalive,
                    checked=lambda ic: self.app.keepalive.is_running()
                ),
                pystray.MenuItem(
                    lambda ic: f"整点通知({self.app.hourly_reminder.is_active}): {self.app.hourly_reminder.next_hour}",
                    self.hourly_reminder,
                    checked=lambda ic: self.app.hourly_reminder.is_active
                ),
                pystray.Menu.SEPARATOR,  # 分隔线
                pystray.MenuItem("设置", self.show_settings),
                pystray.MenuItem("退出", self.exit_app)
            )
        )
        self.update_thread = threading.Thread(target=self.update_menu)
        self.update_thread.start()

    def update_menu(self):
        """更新菜单"""
        logger.info(f"Update menu thread start...")
        while True:
            try:
                time.sleep(5)
                self.icon.update_menu()
            except Exception as e:
                logger.error(f"Update menu failed: {e}")

    def run(self):
        """运行托盘图标"""
        if self.icon:
            self.icon.run()

    def keepalive(self):
        """开一个子线程保持活跃"""
        if self.app.keepalive.is_running():
            self.app.keepalive.stop()
        else:
            self.app.keepalive.start()
            n = 0
            while not self.app.keepalive.is_running():
                time.sleep(1)
                n += 1
                if n > 3:
                    logger.error(f"Keepalive start failed")
                    self.app.keepalive.stop()
                    break
        logger.info(f"Keepalive is_running: {self.app.keepalive.is_running()}")

    def hourly_reminder(self):
        """开一个子线程保持活跃"""
        if self.app.hourly_reminder.is_active:
            self.app.hourly_reminder.stop()
        else:
            self.app.hourly_reminder.start()
        logger.info(f"HourlyReminder is_active: {self.app.hourly_reminder.is_active}")

    def show_history(self, icon, item):
        """显示翻译历史"""
        self.app.root.after(0, self.app.show_history_window)

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
