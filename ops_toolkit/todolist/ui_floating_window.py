#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_floating_window.py
@Author     : LeeCQ
@Date-Time  : 2026/3/2 20:45
"""

import logging
import re
import tkinter as tk
import typing
import webbrowser
from datetime import datetime
from datetime import timedelta
from tkinter import messagebox
from tkinter import ttk
from typing import Callable

from ops_toolkit.todolist.ui_common import ToolTip
from ops_toolkit.todolist.ui_create_window import TodoCreateWindow
from ops_toolkit.todolist.models import TaskStatus
from ops_toolkit.todolist.models import TodolistTaskModel

if typing.TYPE_CHECKING:
    from ops_toolkit.todolist.main import TodoManager

logger = logging.getLogger("ops_toolkit.todolist.ui_floating_window")


class TaskItem:
    def __init__(self, record: TodolistTaskModel, manager: "TodoManager"):
        self.todo: "TodoManager" = manager
        self.record: TodolistTaskModel = record

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

    @staticmethod
    def parse_timedelta_by_str(t: str) -> tuple[int, int, int]:
        """解析时间增量字符串

        :param t: timedelta str  exp: 1d2h3m
        :return: min, hour, day
        """
        _m, _h, _d = 0, 0, 0
        try:
            if "m" in t:
                _m = int(re.findall(r"(\d+)m", t)[0])
            elif "h" in t:
                _h = int(re.findall(r"(\d+)h", t)[0])
            elif "d" in t:
                _d = int(re.findall(r"(\d+)d", t)[0])
            else:
                _h = int(t.strip())
        except (ValueError, IndexError):
            messagebox.showwarning("提示", "请输入正确的时间格式！ ")
        logger.debug(f"timedelta_str解析结果： {t} -> {_m=} {_h=} {_d=}")
        return _m, _h, _d

    def delay_time_by_str(self, t: str):
        """从字符串延迟"""
        minutes, hours, days = self.parse_timedelta_by_str(t)

        do_time = self.record.do_time if self.record.do_time > datetime.now() else datetime.now()
        new_time = do_time + timedelta(hours=hours, minutes=minutes, days=days)
        self.record.do_time = new_time
        self.todo.db_manager.update_task(self.record.id, do_time=new_time)
        self.todo.floating_window.load_tasks()
        self.todo.reminder_manager.change_time(self)

    def delay_time_by_time(self, _t: str):
        new_time = datetime.strptime(_t, "%Y-%m-%d %H:%M:%S")

        if new_time < datetime.now():
            messagebox.showwarning("提示", "请输入一个晚于当前时间的时间~")
            return
        self.record.do_time = new_time
        self.todo.db_manager.update_task(self.record.id, do_time=new_time)
        self.todo.floating_window.load_tasks()

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
            self.todo.update_workdir(self.record.id)

    def on_add_worktime(self, s: str):
        """添加工作时间"""
        _m, _h, _d = self.parse_timedelta_by_str(s)
        minutes = _m + _h * 60 + _d * 60 * 24
        self.todo.db_manager.update_task(self.record.id, work_time_occupied=self.record.work_time_occupied + minutes)
        self.todo.floating_window.load_tasks()

    def on_add_reminder(self):
        self.todo.reminder_manager.add(self)
        self.todo.floating_window.load_tasks()

    def on_cancel_reminder(self):
        self.todo.reminder_manager.cancel(self)
        self.todo.floating_window.load_tasks()

    def on_edit_task(self):
        TodoCreateWindow(self.todo, self.record).show()

    def on_open_workdir(self):
        _ps = self.todo.update_workdir(self.record.id)
        _ps.mkdir(parents=True, exist_ok=True)
        webbrowser.open(str(_ps))


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

    def create_task_row(self, task: TodolistTaskModel, id_):
        """创建任务行：核心是让Label背景匹配行背景"""
        # 行容器（设置背景色）
        logger.debug(f"创建任务行 {id_}：{task.title}")
        bg = ["#FFE6EA", "#FFF4CC"] + ["#FFFFFF"] * 10
        row_frame = tk.Frame(self.tasks_frame, bg=bg[id_], relief="solid", borderwidth=1)
        row_frame.pack(fill="x", pady=1)
        _op = TaskItem(task, self.todo)

        # 2. 时间标签：通过设置label的background为行背景色，实现“透明”
        _is_n = "*" if self.todo.reminder_manager.is_notify(task.id) else " "
        time_label = ttk.Label(
            row_frame,
            text=_is_n + self.show_time(task.do_time),
            style="Task.TLabel",
            width=8,
            # 关键：强制标签背景色和父Frame一致（ttk.Label需用configure动态设置）
            background=bg[id_] if task.do_time >= datetime.now() else "#FF3A30",
        )
        time_label.pack(side="left", padx=5, pady=2)
        self.show_menu_row_time(time_label, _op)

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
        self.show_menu_row_title(name_label, _op)
        ToolTip(name_label, text=task.title + (f"\n{task.desc}" if task.desc else ""))

        # 按钮组：按钮容器背景也匹配行背景
        btn_frame = tk.Frame(row_frame, bg=bg[id_])
        btn_frame.pack(side="right", padx=10, pady=5)

        # 操作按钮（样式不变）
        link_btn = ttk.Button(btn_frame, text="🔗", style="Task.TButton", width=3, command=_op.on_link_click)
        link_btn.pack(side="left", padx=2)

        complete_btn = ttk.Button(btn_frame, text="✅", style="Task.TButton", width=3, command=_op.complete_todo)
        complete_btn.pack(side="left", padx=2)
        self.show_menu_worktime(complete_btn, _op)

        delay_btn = ttk.Button(btn_frame, text="⌛️", style="Task.TButton", width=3,
                               command=lambda: _op.delay_time_by_str("1h"))
        delay_btn.pack(side="left", padx=2)
        self.show_menu_delay(delay_btn, _op)

    @staticmethod
    def show_time(dt: datetime) -> str:
        now = datetime.now()

        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        else:
            days_diff = (dt.date() - now.date()).days
            return f"{dt.strftime('%H:%M')}({days_diff:+})"

    def show_menu_worktime(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        _wto_h = op.record.work_time_occupied / 60
        menu.add_command(label=f"完成 ({_wto_h:.1f})", command=lambda: op.complete_todo())
        menu.add_command(label="5分钟", command=lambda: op.on_add_worktime("5m"))
        menu.add_command(label="10分钟", command=lambda: op.on_add_worktime("10m"))
        menu.add_command(label="15分钟", command=lambda: op.on_add_worktime("15m"))
        menu.add_command(label="30分钟", command=lambda: op.on_add_worktime("30m"))
        menu.add_command(label="60分钟", command=lambda: op.on_add_worktime("1h"))
        menu.add_command(label="自定义",
                         command=lambda: self.customize_input(
                             "输入消耗的时间(m,h,d)",
                             op.on_add_worktime,
                             "1h"
                         ))
        # 2. 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def show_menu_delay(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        menu.add_command(label="15分钟", command=lambda: op.delay_time_by_str("15m"))
        menu.add_command(label="2 小时", command=lambda: op.delay_time_by_str("2h"))
        menu.add_command(label="1 天", command=lambda: op.delay_time_by_str("1d"))
        menu.add_command(
            label="自定义",
            command=lambda: self.customize_input("输入延迟的时间(m,h,d)", op.delay_time_by_str, "2d"))
        menu.add_command(
            label="延迟到指定时间",
            command=lambda: self.customize_input(
                "延迟到(YYYY-mm-dd HH:MM[:SS])",
                op.delay_time_by_time,
                (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        # 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def show_menu_row_time(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        menu.add_command(label="删除", command=lambda: op.on_delete())
        if self.todo.reminder_manager.is_notify(op.record.id):
            menu.add_command(label="取消提醒", command=lambda: op.on_cancel_reminder())
        else:
            menu.add_command(label="添加提醒", command=lambda: op.on_add_reminder())
        # 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def show_menu_row_title(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        menu.add_command(label="修改", command=lambda: op.on_edit_task())
        menu.add_command(label="工作目录", command=lambda: op.on_open_workdir())
        # 绑定鼠标右键事件（<Button-3>是右键，Mac系统是<Button-2>）
        frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))

    def customize_input(self, msg, callback: Callable[[str], None], default=""):
        """自定义输入"""
        window = tk.Toplevel(self.window)
        window.geometry(f"200x100+{window.winfo_pointerx() - 200}+{window.winfo_pointery()}")
        # window.overrideredirect(True)  # 无边框
        window.attributes("-topmost", True)  # 窗口置顶
        # window.resizable(False, False)
        window.attributes('-topmost', True)

        label_frame = ttk.LabelFrame(window, text=f"{msg}：")
        label_frame.pack(fill='x', pady=(10, 0))
        entry = ttk.Entry(label_frame, width=20)
        if default:
            entry.insert(0, default)
        entry.pack(side='left')
        butten = tk.Button(
            label_frame,
            text="确定",
            command=lambda: (callback(entry.get().strip()), window.destroy()))
        butten.pack(side='left', padx=(10, 0))
