#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_translate.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:06
"""

import tkinter as tk
from pathlib import Path
from tkinter import font as tk_font, messagebox
import pyperclip
import logging

logger = logging.getLogger("translate.ui.overlay")


en_font = ('霞鹜文楷等宽 屏幕阅读版', 13,)
zn_font = ('霞鹜文楷等宽 屏幕阅读版', 12,)


class TranslationWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.source_text_widget = None
        self.result_text_widget = None

    def show(self, source_text, translated_text, src_lang, dst_lang):
        """显示翻译结果窗口"""
        # 创建新窗口

        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)  # 无边框
        self.window.attributes("-topmost", True)  # 窗口置顶
        self.window.configure(bg='black')

        # 绑定ESC键关闭窗口
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        # 创建布局
        frame = tk.Frame(self.window, bg='black')
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        source_frame = tk.Frame(frame, bg='black')
        source_frame.grid(row=0, column=0, sticky='w', pady=2)
        label = tk.Label(
            source_frame,
            text=f"{source_text}",
            bg='black',
            fg='orange',
            font=en_font if src_lang == 'en' else zn_font,
            wraplength=300,  # 设置换行宽度（像素）
            justify=tk.LEFT,  # 文本左对
        )
        label.pack(side=tk.LEFT)

        result_frame = tk.Frame(frame, bg='black')
        result_frame.grid(row=1, column=0, sticky='w', pady=2)
        label = tk.Label(
            result_frame,
            text=f"{translated_text}",
            bg='black',
            fg='yellow',
            font=en_font if dst_lang == 'en' else zn_font,
            wraplength=300,  # 设置换行宽度（像素）
            justify=tk.LEFT,  # 文本左对
        )
        label.pack(side=tk.LEFT)

        # 计算窗口大小
        self.window.update_idletasks()  # 更新布局以获取准确尺寸
        min_width = min(frame.winfo_reqwidth(), 400) + 20
        min_height = frame.winfo_reqheight() + 20

        # 计算正方形尺寸，取宽高中的较大值，且不小于400像素
        x = self.app.root.winfo_pointerx()
        y = self.app.root.winfo_pointery()
        self.window.geometry(f"{min_width}x{min_height}+{x}+{y}")
        self.window.resizable(True, True)

        # 允许拖动窗口
        self.window.bind("<Button-1>", self.start_drag)
        self.window.bind("<B1-Motion>", self.on_drag_overlay1)

        # 确保窗口获得焦点
        self.window.focus_force()

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

    def copy_result(self):
        """复制翻译结果到剪贴板"""
        if self.result_text_widget:
            result = self.result_text_widget.get(1.0, tk.END).strip()
            pyperclip.copy(result)
            messagebox.showinfo("成功", "翻译结果已复制到剪贴板")


if __name__ == '__main__':
    import threading, time


    class TmpApp:
        def __init__(self, _root):
            self.root = _root


    _app = TmpApp(tk.Tk())
    window = TranslationWindow(_app)
    window.show("你好", "Hello", 'zh', 'en')
    threading.Thread(target=lambda: (time.sleep(5), _app.root.destroy())).start()
    _app.root.mainloop()
