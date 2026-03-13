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
from tkinter.scrolledtext import ScrolledText as _ScrolledText

from ops_toolkit.todolist.models import TodolistTaskModel
from .models import map_int_to_status

if typing.TYPE_CHECKING:
    from .main import TodoManager
logger = logging.getLogger("ops-toolkit.todolist.ui_create_window")


class ScrolledText(_ScrolledText):
    def get(self, index1="1.0", index2="end-1c"):
        return super().get(index1, index2)


class TodoCreateWindow:
    """待办事项创建窗口"""

    def __init__(self, manager: "TodoManager", task: TodolistTaskModel = None):
        self.window = None
        self.task = task
        self.manager: "TodoManager" = manager
        self.args = {
            "id":      (
                "id",
                ttk.Entry,
                tk.StringVar(value=task.id if task else "创建时自动生成"),
                False
            ),
            "status":  (
                "状态",
                ttk.Combobox,
                tk.StringVar(value=map_int_to_status[task.status if task else 0]),
                ["进行中", "已完成", "已取消"]
            ),
            "title":   (
                "标题",
                ttk.Entry,
                tk.StringVar(value=task.title if task else None),
                True
            ),
            "details": [
                "描述",
                ScrolledText,
                ScrolledText(),
                True
            ],
            "link":    (
                "连接",
                ttk.Entry,
                tk.StringVar(value=task.link if task else None),
                True
            ),
            "do_time": (
                "计划时间",
                ttk.Entry,
                tk.StringVar(value=(
                    task.do_time.strftime("%Y-%m-%d %H:%M:%S")
                    if task else
                    (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
                ),
                True
            ),
        }
        self.show()

    def on_text_enter(self, event):
        """输入框回车事件"""
        current_pos = event.widget.index(tk.INSERT)
        event.widget.insert(tk.INSERT, "\n")
        new_pos = f"{int(current_pos.split('.')[0]) + 1}.0"  # 新行的第0列
        event.widget.mark_set(tk.INSERT, new_pos)
        return "break"

    def show(self):
        """设置创建窗口"""
        self.window = tk.Toplevel()
        self.window.title("创建待办事项")
        self.window.geometry("450x400")
        self.window.resizable(False, False)

        # 设置窗口置顶
        self.window.attributes('-topmost', True)
        self.window.attributes('-topmost', False)

        # 主框架
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill="both", expand=True)

        # 使用for循环创建输入框
        for i, (key, (label_text, _class, var, edit)) in enumerate(self.args.items()):
            label = ttk.Label(main_frame, text=f"{label_text}:", font=("微软雅黑", 10))
            label.grid(row=i, column=0, sticky="w", padx=(0, 10), pady=5)
            entry = _class(main_frame, font=("微软雅黑", 10), state="normal" if edit else "disabled")
            if _class is ttk.Combobox:
                entry.configure(values=edit, textvariable=var)
            elif _class is ScrolledText:
                entry.configure(height=5)
                entry.insert("1.0", self.task.desc if self.task else "")
                entry.bind('<Return>', self.on_text_enter)
                self.args[key][2] = entry
            elif _class is ttk.Entry:
                entry.configure(textvariable=var)
            entry.grid(row=i, column=1, sticky="ew", pady=5)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(self.args), column=0, columnspan=2, pady=20)

        confirm_button = ttk.Button(button_frame, text="确认", command=self.on_confirm_and_exit)
        confirm_button.pack(side="left", padx=(0, 10))

        confirm_button = ttk.Button(button_frame, text="确认并继续添加", command=self.on_confirm)
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

    def on_confirm_and_exit(self):
        """确认并继续添加按钮点击事件"""
        self.on_confirm()
        self.window.destroy()

    def on_confirm(self):
        """确认按钮点击事件"""
        kwargs = {key: var.get() for key, (_, _, var, _) in self.args.items()}
        kwargs.pop("id", None)

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
