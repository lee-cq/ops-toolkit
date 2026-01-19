#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_clipboard.py
@Author     : LeeCQ
@Date-Time  : 2025/12/8 02:22

剪切板展示窗口

"""
import io
import logging
import tkinter as tk
from datetime import datetime
from functools import cached_property
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import ttk

import pyperclip
from PIL import Image

logger = logging.getLogger("ops_toolkit.ui_window_clipboard")


class ClipboardWindow:
    def __init__(self, app):
        self.typ_var = None
        self.text_var = None
        self.time_range_var = None
        self.page_var = None
        self.page_size_var = None

        self.app = app
        self.window = None
        self.tree = None

    def show(self):
        """显示剪切板窗口"""
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("剪切板内容")
        self.window.geometry("800x500")
        self.window.resizable(True, True)
        # 绑定ESC键关闭窗口
        # self.window.bind("<Escape>", lambda e: self.window.destroy())

        # 创建布局
        frame = ttk.Frame(self.window, padding="10")
        frame.pack(fill="both", expand=True)

        # 查询条件
        query_frame = ttk.Frame(frame, padding="10")
        query_frame.pack(fill="x")
        query_frame2 = ttk.Frame(frame, padding="10")
        query_frame2.pack(fill="x")
        # 查询条件 - 类型
        ttk.Label(query_frame, text="类型:").pack(side="left", padx=5)
        self.typ_var = tk.StringVar()
        typ_combo = ttk.Combobox(
            query_frame,
            textvariable=self.typ_var,
            values=["all", "text", "files", "image"],
            width=7)
        typ_combo.pack(side="left", padx=5)
        typ_combo.set("all")
        # 查询条件 - 文本
        ttk.Label(query_frame, text="文本:").pack(side="left", padx=5)
        self.text_var = tk.StringVar()
        text_entry = ttk.Entry(query_frame, textvariable=self.text_var, width=30)
        text_entry.pack(side="left", padx=5)

        # 查询条件 - 分页
        ttk.Label(query_frame, text="分页:").pack(side="left", padx=5)
        self.page_var = tk.StringVar()
        page_entry = ttk.Entry(query_frame, textvariable=self.page_var, width=5)
        page_entry.pack(side="left", padx=5)
        page_entry.insert(0, "1")
        ttk.Label(query_frame, text="每页数量:").pack(side="left", padx=5)
        self.page_size_var = tk.StringVar()
        page_size_entry = ttk.Entry(query_frame, textvariable=self.page_size_var, width=5)
        page_size_entry.pack(side="left", padx=5)
        page_size_entry.insert(0, "50")

        # 查询条件 - 时间范围
        ttk.Label(query_frame2, text="时间范围:").pack(side="left", padx=5)
        self.time_range_var = tk.StringVar()
        time_range_entry = ttk.Entry(query_frame2, textvariable=self.time_range_var, width=40)
        time_range_entry.pack(side="left", padx=5)
        time_range_entry.insert(0,
                                f"{datetime.now().strftime('%Y-%m-%d')} 00:00:00 - "
                                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 查询按钮
        query_button = ttk.Button(query_frame2, text="查询", command=self.update_data)
        query_button.pack(side="left", padx=5)

        # 创建表格
        columns = ("id", "type", "time", "text", "data")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        # 设置列标题
        self.tree.heading("id", text="ID")
        self.tree.heading("type", text="类型")
        self.tree.heading("time", text="时间")
        self.tree.heading("text", text="文本")
        self.tree.heading("data", text="数据")

        # 设置列宽度
        self.tree.column("id", width=10)
        self.tree.column("type", width=50)
        self.tree.column("time", width=140)
        self.tree.column("text", width=300)
        self.tree.column("data", width=20)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # 添加表格
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-Button-1>", self.on_item_double_click)
        self.tree.bind("<Button-3>", self.on_item_right_click)

        self.update_data()

        # 添加按钮 - 清空 - 同步
        button_frame = ttk.Frame(self.window, padding="10")
        button_frame.pack(fill="x")

        export_button = ttk.Button(button_frame, text="导出为CSV", command=self.export_to_file)
        export_button.pack(side="left", padx=5)

        clear_button = ttk.Button(button_frame, text="清空历史", command=self.clear_history)
        clear_button.pack(side="right", padx=5)

    def update_data(self):
        # 刷新主窗口的表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        typ = self.typ_var.get() if self.typ_var.get() != "all" else None
        text = self.text_var.get()
        try:
            time_range = self.time_range_var.get().split("-")
            time_range = (datetime.strptime(time_range[0].strip(), "%Y-%m-%d %H:%M:%S"),
                          datetime.strptime(time_range[1].strip(), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            time_range = None
        try:
            page = int(self.page_var.get())
        except ValueError:
            page = 1
        try:
            page_size = int(self.page_size_var.get())
        except ValueError:
            page_size = 50

        for record in self.app.monitor_clipboard.get_records(
                typ=typ, text=text, time_range=time_range, page=page, page_size=page_size):
            self.tree.insert("", tk.END, values=(
                record.id,
                record.typ,
                record.time.isoformat(),
                record.text[:120] + ("..." if len(record.text) > 120 else ""),
                "双击查看" if record.data is not None else "",
            ))

    def on_item_double_click(self, event):
        """显示详细信息"""
        item = self.tree.identify_row(event.y)
        record = self.app.monitor_clipboard.get_record_by_id(int(self.tree.item(item, "values")[0]))

        detail_window = tk.Toplevel(self.window)
        detail_window.title("剪切板内容详情")
        detail_window.geometry("800x500")
        detail_window.resizable(True, True)
        # 绑定ESC键关闭窗口
        detail_window.bind("<Escape>", lambda e: detail_window.destroy())

        frame = ttk.Frame(detail_window, padding="10")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"时间: {record.time.isoformat()}").pack(anchor="w", pady=(0, 10))
        ttk.Label(frame, text=f"类型: {record.typ}").pack(anchor="w", pady=(0, 10))
        if record.typ == "text":
            ttk.Label(frame, text="文本:").pack(anchor="w")
            text = scrolledtext.ScrolledText(frame, wrap="word", height=6)
            text.pack(fill="both", expand=True, pady=(0, 10))
            text.insert(tk.END, record.text)

        elif record.typ == "image":
            ttk.Label(frame, text=f"图片: {record.text}").pack(anchor="w")
            image = tk.PhotoImage(data=record.data)
            image_label = ttk.Label(frame, image=image)
            image_label.image = image
            image_label.pack(anchor="w", expand=True, pady=(0, 10))

        else:
            ttk.Label(frame, text=f"数据: {record.text}").pack(anchor="w")
            ttk.Label(frame, text="无法预览").pack(anchor="w")

    @cached_property
    def context_menu(self):
        def delete_item():
            selected_item = self.tree.selection()[0]
            self.app.monitor_clipboard.clear_history(int(self.tree.item(selected_item, "values")[0]))

        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label="Delete", command=delete_item)
        menu.add_command(label="复制到剪切板", command=self.copy_to_clipboard)
        return menu

    def copy_to_clipboard(self):
        selected_item = self.tree.selection()[0]
        record = self.app.monitor_clipboard.get_record_by_id(int(self.tree.item(selected_item, "values")[0]))
        if record.typ == "text":
            pyperclip.copy(record.text)
            logger.info(f"复制文本到剪切板: {record.text}")
        elif record.typ == "image":
            output = io.BytesIO()
            image = Image.open(record.data)
            image.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]
            pyperclip.copy(data)
        else:
            messagebox.showwarning("警告", "无法复制该类型的内容到剪切板")

    def on_item_right_click(self, event):
        # 创建右键菜单
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def export_to_file(self):
        pass

    def clear_history(self):
        if messagebox.askyesno("确认", "确定要清空所有历史记录吗？"):
            return self.app.monitor_clipboard.clear_history()
        return False

    def query(self, time_range=None, text=None):
        pass


if __name__ == "__main__":
    from ops_toolkit.config import config

    root = tk.Tk()
    _app = ClipboardWindow(root)
    _app.config = config
    root.mainloop()
