#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : app_hotkey.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:09
"""
from pynput import keyboard
from logging import getLogger
from ops_toolkit.todolist.main import TodoManager

logger = getLogger("ops_toolkit.app.hotkey")


class HotkeyListener:
    def __init__(self, app):
        self.app = app
        self.listener = None
        self.running = False
        self.old_keys = [app.config.hotkey_translate, app.config.hotkey_todo_create, app.config.hotkey_todo_display]
        # 启动监听器
        self.start()

    def on_activate(self):
        """快捷键激活时的处理函数"""
        logger.info("Hotkey activated: %s", self.app.config.hotkey_translate)

        # 在主线程中执行GUI操作
        self.app.root.after(0, self.app.perform_translation)

    def on_todo_create_activate(self):
        """待办事项快捷键激活时的处理函数"""
        logger.info("Todoer create window activated: %s", self.app.config.hotkey_todo_create)
        # 在主线程中显示创建窗口
        self.app.root.after(0, self.app.todoer.show_create_window)

    def on_todo_display_activate(self):
        """待办事项快捷键激活时的处理函数"""
        logger.info("Todoer display window activated: %s", self.app.config.hotkey_todo_display)
        # 在主线程中显示待办事项窗口
        self.app.root.after(0, self.app.todoer.show_display_window)

    def start(self):
        """启动快捷键监听器"""
        if self.running:
            self.stop()

        self.running = True

        try:
            # 创建监听器，同时监听翻译快捷键和待办事项快捷键
            self.listener = keyboard.GlobalHotKeys({
                self.app.config.hotkey_translate:    self.on_activate,
                self.app.config.hotkey_todo_create:  self.on_todo_create_activate,
                self.app.config.hotkey_todo_display: self.on_todo_display_activate,
            })
            self.listener.start()
            logger.info(f"Hotkey listener created: {self.app.config.hotkey_translate} -> self.on_activate")
            logger.info(
                f"Hotkey listener created: {self.app.config.hotkey_todo_create} -> self.on_todo_create_activate, ")
            logger.info(
                f"Hotkey listener created: {self.app.config.hotkey_todo_display} -> self.on_todo_display_activate")
        except Exception as e:
            logger.error(f"Error starting hotkey_translate listener: {e}")
            self.running = False

    def stop(self):
        """停止快捷键监听器"""
        if self.listener and self.running:
            self.listener.stop()
            self.running = False
            logger.info("Hotkey listener stopped")

    def update_hotkey(self):
        """更新快捷键"""
        new_keys = [self.app.config.hotkey_translate,
                    self.app.config.hotkey_todo_create,
                    self.app.config.hotkey_todo_display]
        if new_keys != self.old_keys:
            self.start()
            self.old_keys = new_keys
            logger.info(f"热键更新成功: {new_keys}")

