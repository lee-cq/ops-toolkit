#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_hotkey.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:09
"""
from pynput import keyboard
from logging import getLogger

logger = getLogger("ops_toolkit.app.hotkey")


class HotkeyListener:
    def __init__(self, app):
        self.app = app
        self.hotkey = app.config.hotkey
        self.listener = None
        self.running = False

        # 启动监听器
        self.start()

    def on_activate(self):
        """快捷键激活时的处理函数"""
        logger.info("Hotkey activated: %s", self.hotkey)

        # 在主线程中执行GUI操作
        self.app.root.after(0, self.app.perform_translation)

    def start(self):
        """启动快捷键监听器"""
        if self.running:
            self.stop()

        self.running = True

        try:
            # 创建监听器
            self.listener = keyboard.GlobalHotKeys({
                self.hotkey: self.on_activate
            })
            self.listener.start()
            logger.info(f"Hotkey listener started with hotkey: {self.hotkey}")
        except Exception as e:
            logger.error(f"Error starting hotkey listener: {e}")
            self.running = False

    def stop(self):
        """停止快捷键监听器"""
        if self.listener and self.running:
            self.listener.stop()
            self.running = False
            logger.info("Hotkey listener stopped")

    def update_hotkey(self, new_hotkey):
        """更新快捷键"""
        old_hotkey = self.hotkey
        self.hotkey = new_hotkey
        logger.info(f"Updating hotkey from {old_hotkey} to {new_hotkey}")
        self.start()
