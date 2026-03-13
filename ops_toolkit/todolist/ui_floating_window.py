#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_floating_window.py
@Author     : LeeCQ
@Date-Time  : 2026/3/2 20:45
"""

import logging
import tkinter as tk
import typing
from datetime import datetime

from tkinter import ttk

from ops_toolkit.todolist.ui_common import TaskItem
from ops_toolkit.todolist.ui_common import ToolTip, CommonUI
from ops_toolkit.todolist.models import TodolistTaskModel

if typing.TYPE_CHECKING:
    from ops_toolkit.todolist.main import TodoManager

logger = logging.getLogger("ops_toolkit.todolist.ui_floating_window")


class FloatingWindow(CommonUI):
    """浮动任务窗口"""

    def __init__(self, app, todoer: "TodoManager"):
        super().__init__(app, todoer=todoer)
        self.window: tk.Toplevel | None = None
        self.tasks_frame: ttk.Frame | None = None
        self.window_size = (405, 230)

    def show(self):
        """创建浮动窗口"""
        if self.window and self.window.winfo_exists():
            self.window.focus_force()
            return

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)  # 无边框
        self.window.attributes("-topmost", True)  # 窗口置顶
        self.window.configure(bg='black')
        x, y = self.app.root.winfo_x() + 10, self.app.root.winfo_y() + 10
        self.window.geometry(
            f"{self.window_size[0]}x{self.window_size[1]}+"
            f"{self.app.root.winfo_screenwidth() - self.window_size[0] - 30}+{30}"
        )

        # 主框架
        self.tasks_frame = ttk.Frame(self.window, padding="10")
        self.tasks_frame.pack(fill="both", expand=True)

        # 绑定窗口关闭事件
        self.window.bind("<Escape>", self.on_close)
        # 允许拖动窗口
        self.window.bind("<Button-1>", self.start_drag)
        self.window.bind("<B1-Motion>", self.on_drag_overlay1)
        # 双击改变窗口大小
        self.window.bind("<Double-Button-1>", self.on_double_click)

        self.load_tasks()
        self.window.focus_force()

    def on_close(self, event):
        """关闭窗口"""
        _ = event
        logger.info("关闭浮动窗口")
        self.window.destroy()

    def on_double_click(self, event):
        """双击改变窗口大小"""
        if self.window.winfo_height() == self.window_size[1]:
            logger.debug("扩大窗口")
            self.window.geometry(f"{self.window_size[0]}x{self.window_size[1] * 2}")
        else:
            logger.debug("缩小窗口")
            self.window.geometry(f"{self.window_size[0]}x{self.window_size[1]}")

    def load_tasks(self):
        """加载任务列表"""
        if self.tasks_frame is None:
            return
        logger.info("刷新任务列表")
        tasks = self.todoer.db_manager.top_10_task()
        for item in self.tasks_frame.winfo_children():
            item.destroy()
        for i, task in enumerate(tasks):
            self.create_task_row(task, i)

    def create_task_row(self, task: TodolistTaskModel, id_):
        """创建任务行：核心是让Label背景匹配行背景"""
        # 行容器（设置背景色）
        logger.debug(f"创建任务行 {id_}：{task.title}")
        bg = ["#FFE6EA", "#FFF4CC"] + ["#FFFFFF"] * 10
        row_frame = tk.Frame(self.tasks_frame, bg=bg[id_], relief="solid", borderwidth=1)
        row_frame.pack(fill="x", pady=1)
        _op = TaskItem(task, self.todoer)

        # 2. 时间标签：通过设置label的background为行背景色，实现“透明”
        _is_n = "*" if self.todoer.reminder_manager.is_notify(task.id) else " "
        time_label = ttk.Label(
            row_frame,
            text=_is_n + self.show_time(task.do_time),
            width=10,
            background=bg[id_] if task.do_time >= datetime.now() else "#FF3A30",
            anchor="center",
        )
        time_label.pack(side="left", padx=5, pady=2)
        self.show_menu_row_time(time_label, _op)

        # 3. 任务名称标签：同理，背景色匹配行背景
        name_label = ttk.Label(
            row_frame,
            text=task.title,
            anchor="w",
            background=bg[id_],
            width=20,
        )
        name_label.pack(side="left", fill="x", expand=True, padx=1, pady=2)
        self.show_menu_row_title(name_label, _op)
        ToolTip(name_label, text=task.title + (f"\n{task.desc}" if task.desc else ""))

        # 按钮组：按钮容器背景也匹配行背景
        btn_frame = tk.Frame(row_frame, bg=bg[id_])
        btn_frame.pack(side="right", padx=10, pady=5)

        # 操作按钮（样式不变）
        link_btn = ttk.Button(btn_frame, text="🔗", style="Task.TButton", width=3, command=_op.on_link_click)
        link_btn.pack(side="left", padx=2)

        complete_btn = ttk.Button(btn_frame, text="✅", style="Task.TButton", width=3, command=_op.complete_task)
        complete_btn.pack(side="left", padx=2)
        self.show_menu_worktime(complete_btn, _op)

        delay_btn = ttk.Button(btn_frame, text="⌛️", style="Task.TButton", width=3,
                               command=lambda: _op.delay_time_by_str("1h"))
        delay_btn.pack(side="left", padx=2)
        self.show_menu_delay(delay_btn, _op)
