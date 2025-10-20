#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_history_window.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:03
"""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import ttk


class HistoryWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.tree = None

    def show(self):
        """显示历史记录窗口"""
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("翻译历史记录")
        self.window.geometry("800x500")
        self.window.resizable(True, True)
        # 绑定ESC键关闭窗口
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        # 创建布局
        frame = ttk.Frame(self.window, padding="10")
        frame.pack(fill="both", expand=True)

        # 创建表格
        columns = ("id", "time", "src", "dst", "src_lang", "dst_lang")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        # 设置列标题
        self.tree.heading("id", text="ID")
        self.tree.heading("time", text="时间")
        self.tree.heading("src", text="源文本")
        self.tree.heading("dst", text="翻译结果")
        self.tree.heading("src_lang", text="源语言")
        self.tree.heading("dst_lang", text="目标语言")

        # 设置列宽度
        self.tree.column("id", width=10)
        self.tree.column("time", width=150)
        self.tree.column("src", width=200)
        self.tree.column("dst", width=200)
        self.tree.column("src_lang", width=80)
        self.tree.column("dst_lang", width=80)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 放置表格和滚动条
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 填充数据
        self.update_data()
        # 双击查看完整内容
        self.tree.bind("<Double-1>", self.show_full_record)

        # 按钮区域
        button_frame = ttk.Frame(self.window, padding="10")
        button_frame.pack(fill="x")

        export_button = ttk.Button(button_frame, text="导出为CSV", command=self.export_to_cvs)
        export_button.pack(side="left", padx=5)

        export_button = ttk.Button(button_frame, text="导出到飞书", command=self.export_to_feishu)
        export_button.pack(side="left", padx=5)

        clear_button = ttk.Button(button_frame, text="清空历史", command=self.clear_history)
        clear_button.pack(side="right", padx=5)

    def update_data(self):
        # 刷新主窗口的表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        for record in reversed(self.app.history_manager.get_all_records()):
            self.tree.insert("", tk.END, values=(
                record.id,
                record.time.isoformat(),
                record.src[:50] + ("..." if len(record.src) > 50 else ""),
                record.dst[:50] + ("..." if len(record.dst) > 50 else ""),
                record.src_lang,
                record.dst_lang
            ))

    def show_full_record(self, event):
        """显示选中记录的完整内容"""
        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, "values")

        # 查找完整记录
        full_record = None
        for record in self.app.history_manager.get_all_records():
            if record.time.isoformat() == values[0]:
                full_record = record
                break

        if full_record:
            # 创建详情窗口
            detail_window = tk.Toplevel(self.window)
            detail_window.title("翻译详情")
            detail_window.geometry("600x400")

            # 绑定ESC键关闭窗口
            detail_window.bind("<Escape>", lambda e: detail_window.destroy())

            frame = ttk.Frame(detail_window, padding="10")
            frame.pack(fill="both", expand=True)

            ttk.Label(frame, text=f"时间: {full_record['time']}").pack(anchor="w", pady=(0, 10))
            ttk.Label(frame, text=f"语言: {full_record['src_lang']} → {full_record['dst_lang']}").pack(anchor="w",
                pady=(0, 10))
            ttk.Label(frame, text="源文本:").pack(anchor="w")
            src_text = scrolledtext.ScrolledText(frame, wrap="word", height=6)
            src_text.pack(fill="both", expand=True, pady=(0, 10))
            src_text.insert(tk.END, full_record['src'])
            src_text.configure(state="disabled")

            ttk.Label(frame, text="翻译结果:").pack(anchor=tk.W)
            dst_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=6)
            dst_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            dst_text.insert(tk.END, full_record['dst'])
            dst_text.configure(state="disabled")

            def remove_record():
                if messagebox.askyesno("确认", "确定要删除这条翻译记录吗？此操作不可恢复。"):
                    # 从历史记录中删除
                    self.app.history_manager.remove_record(full_record['id'])
                    detail_window.destroy()
                    self.update_data()

            # 添加删除按钮
            button_frame = ttk.Frame(frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            delete_button = ttk.Button(button_frame, text="删除记录", command=remove_record)
            delete_button.pack(side=tk.RIGHT)

    def export_to_cvs(self):
        """导出历史记录为CSV"""
        if not self.app.history_manager.get_all_records():
            messagebox.showinfo("提示", "没有翻译记录可导出")
            return

        # 导出到用户桌面
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_name = f"translation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = os.path.join(desktop_path, file_name)

        if self.app.history_manager.export_to_csv(file_path):
            messagebox.showinfo("成功", f"历史记录已导出到:\n{file_path}")
        else:
            messagebox.showerror("错误", "导出历史记录失败")

    def export_to_feishu(self):
        """导出到飞书"""
        title = "Translation History Export to Feishu"
        try:
            msg = self.app.history_manager.export_feishu()
            messagebox.showinfo(title, msg)
        except (PermissionError, ValueError) as e:
            messagebox.showerror(title, str(e))

    def clear_history(self):
        """清空历史记录"""
        if not self.app.history_manager.get_all_records():
            messagebox.showinfo("提示", "翻译记录已为空")
            return

        if messagebox.askyesno("确认", "确定要清空所有翻译记录吗？此操作不可恢复。"):
            self.app.history_manager.clear_history()
            # 刷新表格
            for item in self.tree.get_children():
                self.tree.delete(item)
            messagebox.showinfo("成功", "翻译记录已清空")
