#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_create_window.py
@Author     : LeeCQ
@Date-Time  : 2026/2/5 00:57
"""

import tkinter as tk
import typing
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import logging

from ops_toolkit.todolist.models import TodolistTaskModel

if typing.TYPE_CHECKING:
    from .main import TodoManager
logger = logging.getLogger("ops-toolkit.todolist.ui_create_window")


class TodoCreateWindow:
    """待办事项创建窗口"""

    def __init__(self, manager: "TodoManager", task: TodolistTaskModel = None):
        self.window = None
        self.task = task
        self.manager: "TodoManager" = manager
        self.args = {
            "title":   ("标题", tk.StringVar(value=task.title if task else None)),
            "desc":    ("描述", tk.StringVar(value=task.desc if task else None)),
            "link":    ("连接", tk.StringVar(value=task.link if task else None)),
            "do_time": ("计划时间",
                        tk.StringVar(value=(
                            task.do_time.strftime("%Y-%m-%d %H:%M:%S")
                            if task else
                            (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
                        )),
        }
        self.show()

    def show(self):
        """设置创建窗口"""
        self.window = tk.Toplevel()
        self.window.title("创建待办事项")
        self.window.geometry("450x260")
        self.window.resizable(False, False)

        # 设置窗口置顶
        self.window.attributes('-topmost', True)
        self.window.attributes('-topmost', False)

        # 主框架
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill="both", expand=True)

        # 使用for循环创建输入框
        for i, (key, (label_text, var)) in enumerate(self.args.items()):
            label = ttk.Label(main_frame, text=f"{label_text}:", font=("微软雅黑", 10))
            label.grid(row=i, column=0, sticky="w", padx=(0, 10), pady=5)
            entry = ttk.Entry(main_frame, textvariable=var, font=("微软雅黑", 10))
            entry.grid(row=i, column=1, sticky="ew", pady=5)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        confirm_button = ttk.Button(button_frame, text="确认", command=self.on_confirm)
        confirm_button.pack(side="left", padx=(0, 10))

        cancel_button = ttk.Button(button_frame, text="取消", command=self.window.destroy)
        cancel_button.pack(side="left")

        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)

        # 绑定回车键
        self.window.bind('<Return>', lambda e: self.on_confirm())
        self.window.bind('<Escape>', lambda e: self.window.destroy())

        # 窗口居中显示
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def on_confirm(self):
        """确认按钮点击事件"""
        kwargs = {key: var.get() for key, (_, var) in self.args.items()}

        if not kwargs["title"]:
            messagebox.showwarning("提示", "请输入标题")
            return

        try:
            # noinspection PyTypeChecker
            kwargs["do_time"] = datetime.strptime(kwargs["do_time"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            messagebox.showwarning("提示", "请输入正确的时间格式")
            return
        if self.task:
            self.manager.db_manager.update_task(self.task.id, **kwargs)
            self.manager.update_window()
            self.window.destroy()
        else:
            self.manager.db_manager.add_task(**kwargs)
            self.manager.update_window()
