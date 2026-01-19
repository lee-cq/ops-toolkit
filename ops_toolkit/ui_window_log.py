#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_log.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:04
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging

logger = logging.getLogger("ops_toolkit.ui.window_log")


class LogWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.text_widget = None

    def show(self):
        """显示日志窗口"""
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("应用程序日志")
        self.window.geometry("800x500")
        self.window.resizable(True, True)

        # 创建布局
        frame = ttk.Frame(self.window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # 日志文本区域
        self.text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.configure(state="disabled")

        # 加载日志内容
        self.load_logs()

        # 按钮区域
        button_frame = ttk.Frame(self.window, padding="10")
        button_frame.pack(fill=tk.X)

        refresh_button = ttk.Button(button_frame, text="刷新", command=self.load_logs)
        refresh_button.pack(side=tk.LEFT, padx=5)

        dir_butten = ttk.Button(button_frame, text="打开所在文件夹", command=self.open_log_dir)
        dir_butten.pack(side=tk.LEFT, padx=5)

        clear_button = ttk.Button(button_frame, text="清空日志", command=self.clear_logs)
        clear_button.pack(side=tk.RIGHT, padx=5)

    def load_logs(self):
        """加载日志内容"""
        try:
            if os.path.exists(self.app.config.log_path):
                self.text_widget.configure(state="normal")
                self.text_widget.delete(1.0, tk.END)

                with open(self.app.config.log_path, 'r', encoding='utf-8') as f:
                    # 只显示最后1000行，避免日志过大
                    lines = f.readlines()
                    if len(lines) > 1000:
                        lines = lines[-1000:]
                    self.text_widget.insert(tk.END, ''.join(lines))

                # 滚动到最后
                self.text_widget.see(tk.END)
                self.text_widget.configure(state="disabled")
        except Exception as e:
            logger.error(f"Error loading logs: {e}")

    def clear_logs(self):
        """清空日志文件"""
        if messagebox.askyesno("确认", "确定要清空日志吗？"):
            try:
                if os.path.exists(self.app.config.log_path):
                    os.remove(self.app.config.log_path)
                    # 刷新显示
                    self.text_widget.configure(state="normal")
                    self.text_widget.delete(1.0, tk.END)
                    self.text_widget.configure(state="disabled")
                    logger.info("Logs cleared by user")
                    messagebox.showinfo("成功", "日志已清空")
            except Exception as e:
                logger.error(f"Error clearing logs: {e}")
                messagebox.showerror("错误", "清空日志失败")

    def open_log_dir(self):
        import os
        os.startfile(self.app.config.log_path.parent)