#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_summary.py
@Author     : LeeCQ
@Date-Time  : 2026/3/2 20:14
"""
import logging
import typing
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from .ui_common import CommonUI
from .ui_common import TaskItem
from .ui_common import ToolTip

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App
    from .main import TodoManager
    from .models import TodolistTaskModel

logger = logging.getLogger("ops_toolkit.todolist.ui_summary")


class TreeTip(ToolTip):

    def __init__(self, sum_window: "SummaryWindow", text=""):
        super().__init__(sum_window.tasks_tree, text)
        self.sw = sum_window

    def _show_tooltip(self, event=None):
        _, row = self.sw.get_row_info(event)
        if _ != "title":
            return
        self.text = self.sw.cached_tasks[row[0]].desc
        super()._show_tooltip(event)


class SummaryWindow(CommonUI):

    def __init__(self, app: "App", todoer: "TodoManager"):
        super().__init__(app, todoer=todoer)
        self.window: tk.Toplevel | None = None
        self.tasks_frame: ttk.Frame | None = None
        self.tasks_tree: ttk.Treeview | None = None

        self.query_var = tk.StringVar()
        self.order_bys: dict[str, str] = {  # 排序字段
            "id": "asc",
        }

        self.columns = {
            "id":                 ["ID", 20, "c"],
            "status":             ["状态", 30, "c"],
            "title":              ["标题", 260, "w"],
            "create_time":        ["创建时间", 100, "c"],
            "do_time":            ["最后更新时间", 100, "c"],
            "work_time_occupied": ["耗时", 50, "c"],
        }

        self.cached_tasks: dict[int, "TodolistTaskModel"] = dict()

    def show(self):
        if self.window:
            if self.window.winfo_exists():
                self.window.focus_force()
                return
            else:
                self.window.destroy()
                self.window = None

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        # self.window.overrideredirect(True)  # 无边框
        # self.window.attributes("-topmost", True)  # 窗口置顶
        self.window.geometry("850x550")
        self.window.configure(bg='black')
        # 绑定窗口关闭事件
        self.window.bind("<Escape>", self.on_close)
        # 允许拖动窗口
        # self.window.bind("<Button-1>", self.start_drag)
        # self.window.bind("<B1-Motion>", self.on_drag_overlay1)

        # 查询框架
        query_frame = ttk.LabelFrame(self.window, text="查询", padding=10)
        query_frame.pack(side="top", fill="x")
        query_entry = ttk.Entry(query_frame, textvariable=self.query_var, font=("Consolas", 10))
        query_entry.pack(side="left", fill="x", expand=True)
        query_btn = ttk.Button(query_frame, text="查询", command=lambda: self.load_tasks())
        query_btn.pack(side="right")

        # 主框架
        self.tasks_frame = ttk.Frame(self.window, padding="10")
        self.tasks_frame.pack(fill="both", expand=True)

        self.tasks_tree = ttk.Treeview(self.tasks_frame, columns=list(self.columns.keys()), show="headings")
        for column, (text, width, anchor) in self.columns.items():
            self.tasks_tree.heading(column, text=text, command=lambda c=column: self.load_tasks(order_bys=[c]))
            self.tasks_tree.column(column, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(self.tasks_frame, orient="vertical", command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)

        # 放置表格和滚动条
        self.tasks_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.load_tasks()
        self.tasks_tree.bind("<Double-1>", self.show_task_detail)
        self.tasks_tree.bind("<Button-3>", self.show_menu)

        # self.window.focus_force()
        button_frame = ttk.Frame(self.window, padding="10")
        button_frame.pack(fill="x")
        export_button = ttk.Button(button_frame, text="导出为CSV", command=self.export_to_cvs)
        export_button.pack(side="left", padx=5)

    def on_close(self, event):
        """关闭窗口"""
        _ = event
        logger.info("关闭todoer窗口")
        self.window.destroy()

    def load_tasks(self, query: str = "", order_bys: list[str] = None):
        if not (
                self.tasks_tree
                and self.window
                and self.tasks_frame
                and self.tasks_frame.winfo_exists()
                and self.tasks_tree.winfo_exists()
        ):
            return
        if query:
            self.query_var.set(query)
        if order_bys:
            for k in order_bys:
                _ac = "asc" if self.order_bys.pop(k, "desc") == "desc" else "desc"
                self.order_bys = {k: _ac} | self.order_bys

        tasks = self.todoer.db_manager.query_task(
            self.query_var.get().strip(),
            [(k, v) for k, v in self.order_bys.items()]
        )
        if not tasks:
            messagebox.showinfo("提示", "没有查询到任务")
            return
        # 清空表格数据而不是销毁组件
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        self.cached_tasks = {}
        for task in tasks:
            self.cached_tasks[task.id] = task
            logger.debug(f"添加列：{task.id}, {task.title}")
            self.tasks_tree.insert("", "end", values=(
                task.id,
                task.status_emoji(),
                task.title,
                task.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                task.do_time.strftime("%Y-%m-%d %H:%M:%S"),
                f"{task.work_time_occupied:.2f} h"
            ))

    def get_row_info(self, event) -> tuple[str, list]:
        _tree = event.widget
        region = _tree.identify("region", event.x, event.y)
        if region == "cell":
            row_id = _tree.identify_row(event.y)  # 点击的行ID（如I001）
            col_id = _tree.identify_column(event.x)  # 点击的列ID（如#1）
            row_data = _tree.item(row_id)["values"]  # 行的所有值
            col_index = int(col_id.replace("#", "")) - 1  # 列索引（从0开始）
            return tuple(self.columns.keys())[col_index], row_data
        raise ValueError(f"无效的点击区域, {region=}")

    def show_task_detail(self, event):
        _, row = self.get_row_info(event)
        op = TaskItem(self.cached_tasks[row[0]], self.todoer)
        op.on_edit_task()

    def show_menu_set_status(self, frame, op: "TaskItem"):
        menu = tk.Menu(frame, tearoff=0)
        menu.add_command(label="进行中", command=lambda: op.set_status(0))
        menu.add_command(label="已完成", command=lambda: op.set_status(1))
        menu.add_command(label="已取消", command=lambda: op.set_status(2))
        if type(self).__name__ == "FloatingWindow":
            frame.bind("<Button-3>", lambda event: menu.post(event.x_root, event.y_root))
        return menu

    def show_menu(self, event):
        col, row = self.get_row_info(event)
        op = TaskItem(self.cached_tasks[row[0]], self.todoer)
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_cascade(label="延迟", menu=self.show_menu_delay(menu, op))
        menu.add_cascade(label="操作", menu=self.show_menu_row_title(menu, op))
        menu.add_cascade(label="添加工时", menu=self.show_menu_worktime(menu, op))
        menu.add_cascade(label="设置状态", menu=self.show_menu_set_status(menu, op))

        menu.tk_popup(event.x_root, event.y_root)

    def export_to_cvs(self):
        """导出任务列表为CSV"""
