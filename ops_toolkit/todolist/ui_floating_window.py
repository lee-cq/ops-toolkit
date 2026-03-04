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
import webbrowser
from datetime import datetime
from datetime import timedelta
from tkinter import messagebox
from tkinter import ttk

from ops_toolkit.todolist.models import TaskStatus
from ops_toolkit.todolist.models import TodolistModel

if typing.TYPE_CHECKING:
    from ops_toolkit.todolist.main import TodoManager

logger = logging.getLogger("ops_toolkit.todolist.ui_floating_window")


class TaskItem:
    def __init__(self, record: TodolistModel, manager: "TodoManager"):
        self.todo: "TodoManager" = manager
        self.record: TodolistModel = record

    def on_link_click(self):
        if self.record.link:
            webbrowser.open(self.record.link)

    def on_delete(self):
        if messagebox.askyesno(
                "提示",
                f"确定要删除任务吗？\n"
                f"{self.record.id} {self.record.title} (已经花费{self.record.work_time_occupied / 60:.2f}小时)"
        ):
            self.todo.db_manager.update_task(self.record, status=TaskStatus.DELETE)
            self.todo.reminder_manager.cancel(self)
            self.todo.floating_window.load_tasks()

    def delay_time(self, hours=1, minutes=0, days=0):
        do_time = self.record.do_time if self.record.do_time > datetime.now() else datetime.now()
        new_time = do_time + timedelta(hours=hours, minutes=minutes, days=days)
        self.record.do_time = new_time
        self.todo.db_manager.update_task(self.record.id, do_time=new_time)
        self.todo.floating_window.load_tasks()
        self.todo.reminder_manager.change_time(self)

    def complete_todo(self):
        """完成待办事项"""
        if messagebox.askyesno(
                "提示",
                "确定要完成此任务吗？\n"
                f"{self.record.id} {self.record.title} (已经花费{self.record.work_time_occupied / 60:.2f}小时)"
        ):
            self.todo.db_manager.complete_task(self.record.id)
            self.todo.reminder_manager.cancel(self)
            self.todo.floating_window.load_tasks()

    def on_add_worktime(self, minutes=1):
        minutes = int(minutes)
        self.todo.db_manager.update_task(self.record.id, work_time_occupied=self.record.work_time_occupied + minutes)
        self.todo.floating_window.load_tasks()

    def on_add_reminder(self):
        self.todo.reminder_manager.add(self)


class FloatingWindow:
    """浮动任务窗口"""

    def __init__(self, app, manager: "TodoManager"):
        self.app = app
        self.todo = manager
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

    def start_drag(self, event):
        """开始拖动浮窗1"""
        self.x1 = event.x
        self.y1 = event.y

    def on_double_click(self, event):
        """双击改变窗口大小"""
        if self.window.winfo_height() == self.window_size[1]:
            logger.debug("扩大窗口")
            self.window.geometry(f"{self.window_size[0]}x{self.window_size[1] * 2}")
        else:
            logger.debug("缩小窗口")
            self.window.geometry(f"{self.window_size[0]}x{self.window_size[1]}")

    def on_drag_overlay1(self, event):
        """拖动浮窗1时更新位置"""
        x = self.window.winfo_x() + event.x - self.x1
        y = self.window.winfo_y() + event.y - self.y1
        self.window.geometry(f"+{x}+{y}")
        # logger.debug(f"浮窗1位置更新: x={x}, y={y}")

    def load_tasks(self):
        """加载任务列表"""
        # 清空现有任务
        logger.info("刷新任务列表")
        for item in self.tasks_frame.winfo_children():
            item.destroy()

        # 获取未完成的任务
        tasks = self.todo.db_manager.top_10_task()

        # 创建任务项
        for i, task in enumerate(tasks):
            self.create_task_row(task, i)

    def create_task_row(self, task: TodolistModel, id_):
        """创建任务行：核心是让Label背景匹配行背景"""
        # 行容器（设置背景色）
        logger.debug(f"创建任务行 {id_}：{task.title}")
        bg = ["#FFE6EA", "#FFF4CC"] + ["#FFFFFF"] * 10
        row_frame = tk.Frame(self.tasks_frame, bg=bg[id_], relief="solid", borderwidth=1)
        row_frame.pack(fill="x", pady=1)
        _op = TaskItem(task, self.todo)

        # 2. 时间标签：通过设置label的background为行背景色，实现“透明”
        time_label = ttk.Label(
            row_frame,
            text=self.show_time(task.do_time),
            style="Task.TLabel",
            width=8,
            # 关键：强制标签背景色和父Frame一致（ttk.Label需用configure动态设置）
            background=bg[id_]
        )
        time_label.pack(side="left", padx=5, pady=2)
        self.show_frame_row_menu(time_label, _op)

        # 3. 任务名称标签：同理，背景色匹配行背景
        name_label = ttk.Label(
            row_frame,
            text=task.title,
            style="Task.TLabel",
            anchor="w",
            background=bg[id_],
            width=20,
        )
        name_label.pack(side="left", fill="x", expand=True, padx=0, pady=2)

        # 按钮组：按钮容器背景也匹配行背景
        btn_frame = tk.Frame(row_frame, bg=bg[id_])
        btn_frame.pack(side="right", padx=10, pady=5)

        # 操作按钮（样式不变）
        link_btn = ttk.Button(btn_frame, text="🔗", style="Task.TButton", width=3, command=_op.on_link_click)
        link_btn.pack(side="left", padx=2)

        complete_btn = ttk.Button(btn_frame, text="✅", style="Task.TButton", width=3, command=_op.complete_todo)
        complete_btn.pack(side="left", padx=2)
        self.show_worktime_menu(complete_btn, _op)

        delay_btn = ttk.Button(btn_frame, text="⌛️", style="Task.TButton", width=3, command=lambda: _op.delay_time(1, ))
        delay_btn.pack(side="left", padx=2)
        self.show_delay_menu(delay_btn, _op)

    @staticmethod
    def show_time(dt: datetime) -> str:
        now = datetime.now()

        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        else:
            days_diff = (dt.date() - now.date()).days
            return f"{dt.strftime('%H:%M')}({days_diff:+})"

    def show_worktime_menu(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        _wto_h = op.record.work_time_occupied / 60
        menu.add_command(label=f"完成 ({_wto_h:.1f})", command=lambda: op.complete_todo())
        menu.add_command(label="5分钟", command=lambda: op.on_add_worktime(5))
        menu.add_command(label="10分钟", command=lambda: op.on_add_worktime(10))
        menu.add_command(label="15分钟", command=lambda: op.on_add_worktime(15))
        menu.add_command(label="30分钟", command=lambda: op.on_add_worktime(30))
        menu.add_command(label="60分钟", command=lambda: op.on_add_worktime(60))
        menu.add_command(label="自定义",
                         command=lambda: self.customize_input("输入消耗的时间(分钟)", op.on_add_worktime))
        # 2. 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def show_delay_menu(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        menu.add_command(label="10分钟", command=lambda: op.delay_time(hours=0, minutes=10))
        menu.add_command(label="30分钟", command=lambda: op.delay_time(hours=0, minutes=30))
        menu.add_command(label="2 小时", command=lambda: op.delay_time(hours=2))
        menu.add_command(label="1 天", command=lambda: op.delay_time(hours=24))
        menu.add_command(label="自定义", command=lambda: self.customize_input("输入延迟的时间(小时)", op.delay_time))
        # 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def show_frame_row_menu(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        menu.add_command(label="删除", command=lambda: op.on_delete())
        menu.add_command(label="添加提醒", command=lambda: op.on_add_reminder())
        # 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def customize_input(self, msg, callback):
        """自定义输入"""
        window = tk.Toplevel(self.window)
        window.geometry(f"200x100+{window.winfo_pointerx() - 200}+{window.winfo_pointery()}")
        # window.overrideredirect(True)  # 无边框
        window.attributes("-topmost", True)  # 窗口置顶
        # window.resizable(False, False)
        window.attributes('-topmost', True)

        label_frame = ttk.LabelFrame(window, text=f"{msg}：")
        label_frame.pack(fill='x', pady=(10, 0))
        entry = ttk.Entry(label_frame, width=10)
        entry.pack(side='left')
        butten = tk.Button(label_frame, text="确定",
                           command=lambda: (callback(float(entry.get().strip())), window.destroy()))
        butten.pack(side='left', padx=(10, 0))
