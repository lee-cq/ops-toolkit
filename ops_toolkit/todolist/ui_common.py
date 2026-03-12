#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_common.py
@Author     : LeeCQ
@Date-Time  : 2026/3/7 01:12
"""
import logging
import re
import typing
import tkinter as tk
import webbrowser
from datetime import datetime
from datetime import timedelta
from tkinter import messagebox
from tkinter import ttk

from ops_toolkit.todolist.ui_create_window import TodoCreateWindow
from ops_toolkit.todolist.models import TaskStatus

if typing.TYPE_CHECKING:
    from ops_toolkit.todolist.main import TodoManager
    from ops_toolkit.todolist.main import TodolistTaskModel
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.todolist.ui_common")

map_status_to_emoji = {
    0: "🔄",
    1: "🎉",
    2: "❌",
}

map_status_to_int = {
    "进行中": 0,
    "已完成": 1,
    "已取消": 2,
}
map_int_to_status = {v: k for k, v in map_status_to_int.items()}


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


class TaskItem:
    def __init__(self, record: "TodolistTaskModel", manager: "TodoManager"):
        self.todoer: "TodoManager" = manager
        self.record: "TodolistTaskModel" = record

    def on_link_click(self):
        if self.record.link:
            webbrowser.open(self.record.link)

    def on_delete(self):
        if messagebox.askyesno(
                "提示",
                f"确定要删除任务吗？\n"
                f"{self.record.id} {self.record.title} (已经花费{self.record.work_time_occupied / 60:.2f}小时)"
        ):
            self.todoer.db_manager.update_task(self.record, status=TaskStatus.DELETE)
            self.todoer.reminder_manager.cancel(self)
            self.todoer.floating_window.load_tasks()
            self.todoer.summary.load_tasks()

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
        self.todoer.db_manager.update_task(self.record.id, do_time=new_time)
        self.todoer.floating_window.load_tasks()
        self.todoer.summary.load_tasks()
        self.todoer.reminder_manager.change_time(self)

    def delay_time_by_time(self, _t: str):
        new_time = datetime.strptime(_t, "%Y-%m-%d %H:%M:%S")

        if new_time < datetime.now():
            messagebox.showwarning("提示", "请输入一个晚于当前时间的时间~")
            return
        self.record.do_time = new_time
        self.todoer.db_manager.update_task(self.record.id, do_time=new_time)
        self.todoer.floating_window.load_tasks()
        self.todoer.summary.load_tasks()

    def complete_todo(self):
        """完成待办事项"""
        return self.set_status(1)

    def set_status(self, status: int):
        """设置任务状态"""
        if self.record.status == status:
            messagebox.showwarning("提示", "请勿重复设置任务状态")
            return

        if messagebox.askyesno(
                "提示",
                f"确定要将状态设置为「{map_int_to_status[status]}」吗？\n"
                f"{self.record.id} {self.record.title} (已经花费{self.record.work_time_occupied / 60:.2f}小时)"
        ):
            self.todoer.db_manager.update_task(self.record.id, status=status)
            self.todoer.reminder_manager.cancel(self)
            self.todoer.floating_window.load_tasks()
            self.todoer.summary.load_tasks()
            self.todoer.update_workdir(self.record.id)
            return

    def on_add_worktime(self, s: str):
        """添加工作时间"""
        _m, _h, _d = self.parse_timedelta_by_str(s)
        minutes = _m + _h * 60 + _d * 60 * 24
        self.todoer.db_manager.update_task(self.record.id, work_time_occupied=self.record.work_time_occupied + minutes)
        self.todoer.floating_window.load_tasks()
        self.todoer.summary.load_tasks()

    def on_add_reminder(self):
        self.todoer.reminder_manager.add(self)
        self.todoer.floating_window.load_tasks()
        self.todoer.summary.load_tasks()

    def on_cancel_reminder(self):
        self.todoer.reminder_manager.cancel(self)
        self.todoer.floating_window.load_tasks()
        self.todoer.summary.load_tasks()

    def on_edit_task(self):
        TodoCreateWindow(self.todoer, self.record)

    def on_open_workdir(self):
        _ps = self.todoer.update_workdir(self.record.id)
        _ps.mkdir(parents=True, exist_ok=True)
        webbrowser.open(str(_ps))


class CommonUI:

    def __init__(self, app: "App", todoer: "TodoManager"):
        self.app: "App" = app
        self.todoer: "TodoManager" = todoer
        self.window: tk.Toplevel | None = None

    def start_drag(self, event):
        """开始拖动浮窗1"""
        self.x1 = event.x
        self.y1 = event.y

    def on_drag_overlay1(self, event):
        """拖动浮窗1时更新位置"""
        x = self.window.winfo_x() + event.x - self.x1
        y = self.window.winfo_y() + event.y - self.y1
        self.window.geometry(f"+{x}+{y}")
        # logger.debug(f"浮窗1位置更新: x={x}, y={y}")

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
        if type(self).__name__ == "FloatingWindow":
            frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))
        return menu

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
        if type(self).__name__ == "FloatingWindow":
            frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))
        return menu

    def show_menu_row_time(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        if self.todoer.reminder_manager.is_notify(op.record.id):
            menu.add_command(label="取消提醒", command=lambda: op.on_cancel_reminder())
        else:
            menu.add_command(label="添加提醒", command=lambda: op.on_add_reminder())
        if type(self).__name__ == "FloatingWindow":
            frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))
        return menu

    def show_menu_row_title(self, frame, op: TaskItem):
        menu = tk.Menu(frame, tearoff=False)
        menu.add_command(label="工作目录", command=lambda: op.on_open_workdir())
        menu.add_command(label="修改", command=lambda: op.on_edit_task())
        menu.add_command(label="删除", command=lambda: op.on_delete())

        if type(self).__name__ == "FloatingWindow":
            frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))
        return menu

    def customize_input(self, msg, callback: typing.Callable[[str], None], default=""):
        """自定义输入"""
        window = tk.Toplevel(self.app.root)
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
