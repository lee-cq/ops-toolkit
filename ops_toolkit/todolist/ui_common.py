#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_common.py
@Author     : LeeCQ
@Date-Time  : 2026/3/7 01:12
"""
import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger("ops_toolkit.todolist.ui_common")


class ToolTip:
    """自定义ToolTip类，实现鼠标悬停提示功能"""

    def __init__(self, widget, text="提示信息"):
        self.widget = widget  # 绑定的组件
        self.text = text  # 提示文字
        self.tooltip = None  # 提示框窗口
        self.id = None  # 延迟显示的任务ID

        # 绑定鼠标事件
        self.widget.bind('<Enter>', self._show_tooltip)
        self.widget.bind('<Leave>', self._hide_tooltip)
        self.widget.bind('<ButtonPress>', self._hide_tooltip)  # 点击组件时也隐藏

    def _show_tooltip(self, event=None):
        """显示提示框（添加小延迟，避免鼠标快速划过触发）"""
        self.id = self.widget.after(100, self._create_tooltip)

    def _create_tooltip(self):
        """创建并显示提示框"""
        if self.tooltip or not self.text:
            return

        # 获取组件的位置，让提示框显示在组件右下方
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20

        # 创建顶级临时窗口作为提示框
        self.tooltip = tk.Toplevel(self.widget)
        # 设置为无标题栏的临时窗口
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.attributes("-topmost", True)  # 窗口置顶
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # 创建提示框内容标签
        label = ttk.Label(
            self.tooltip,
            text=self.text,
            background="#ffffe0",  # 浅黄色背景
            foreground="#333333",  # 深灰色文字
            relief="solid",  # 边框
            borderwidth=1,
            padding=(5, 2)  # 内边距
        )
        label.pack()

    def _hide_tooltip(self, event=None):
        """隐藏提示框"""
        # 取消延迟显示的任务
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

        # 销毁提示框
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
