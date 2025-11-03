#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_translate.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:06
"""
import logging
import os
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tk_font
from tkinter import messagebox

import pyperclip
from win11toast import notify

logger = logging.getLogger("translate.ui.overlay")

font_dir = Path(__file__).parent.joinpath("resources")

en_font = ('霞鹜文楷等宽 Medium', 13,)
zn_font = ('霞鹜文楷等宽 Medium', 12,)


class TranslationWindow:
    def __init__(self, app):
        self.y1 = None
        self.x1 = None
        self.app = app
        self.window = None
        self.dst_text = None

        if not [i for i in tk_font.families() if i == "霞鹜文楷等宽 Medium"]:
            from lzma import decompress
            font_dir.joinpath("LXGWWenKaiMono-Medium.ttf").write_bytes(
                decompress(font_dir.joinpath("LXGWWenKaiMono-Medium.ttf.lzma.py").read_bytes())
            )
            tk.messagebox.showinfo("安装字体", "点击确定后开始安装字体，完成后手动关闭字体窗口继续。")
            os.system(font_dir.joinpath("LXGWWenKaiMono-Medium.ttf").absolute().__str__())

    def show(self, source_text, translated_text, src_lang, dst_lang, width=300):
        """显示翻译结果窗口"""
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)  # 无边框
        self.window.attributes("-topmost", True)  # 窗口置顶
        self.window.configure(bg='black')
        self.dst_text = translated_text
        # 绑定ESC键关闭窗口
        self.window.bind("<Escape>", lambda e: self.window.destroy())
        # 绑定双击事件执行copy_result
        self.window.bind("<Double-1>", lambda e: self.copy_result())
        # 允许拖动窗口
        self.window.bind("<Button-1>", self.start_drag)
        self.window.bind("<B1-Motion>", self.on_drag_overlay1)

        # 创建布局
        frame = tk.Frame(self.window, bg='black')
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        source_frame = tk.Frame(frame, bg='black')
        source_frame.grid(row=0, column=0, sticky='w', pady=2)
        label = tk.Label(
            source_frame,
            text=f"{source_text}",
            bg='black',
            fg='orange',
            font=en_font if src_lang == 'en' else zn_font,
            wraplength=width,  # 设置换行宽度（像素）
            justify="left",  # 文本左对
        )
        label.pack(side="left")

        result_frame = tk.Frame(frame, bg='black')
        result_frame.grid(row=1, column=0, sticky='w', pady=2)
        label = tk.Label(
            result_frame,
            text=f"{translated_text}",
            bg='black',
            fg='yellow',
            font=en_font if dst_lang == 'en' else zn_font,
            wraplength=width,  # 设置换行宽度（像素）
            justify="left",  # 文本左对
        )
        label.pack(side="left")

        # 计算窗口大小
        self.window.update_idletasks()  # 更新布局以获取准确尺寸
        min_width = min(frame.winfo_reqwidth(), width) + 20
        min_height = frame.winfo_reqheight() + 20
        if min_height > min_width * 1.3:
            return self.show(
                source_text,
                translated_text,
                src_lang,
                dst_lang,
                width=800, )

        x = self.app.root.winfo_pointerx()
        y = self.app.root.winfo_pointery()
        logger.debug(f"windowSize = {min_width}x{min_height}+{x}+{y}")
        self.window.geometry(f"{min_width}x{min_height}+{x}+{y}")
        self.window.resizable(True, True)

        # 确保窗口获得焦点
        self.window.focus_force()
        return None

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
        logger.info("双击事件触发：复制翻译结果到剪贴板")
        if self.dst_text:
            pyperclip.copy(self.dst_text)
            notify("翻译结果已复制到剪贴板", self.dst_text, app_id=self.app.config.app_name)
            time.sleep(0.5)
            self.window.destroy()


if __name__ == '__main__':
    from tkinter import ttk


    class TmpApp:
        def __init__(self, _root):
            self.root = _root

            # 按钮区域
            button_frame = ttk.Frame(_root)
            button_frame.pack(fill="x", pady=10)

            save_button = ttk.Button(button_frame, text="show", command=show)
            save_button.pack(side="right", padx=5)


    def show():
        window.show(
            "你好",
            str(Path(__file__).parent.joinpath("resources/LXGWWenKaiMono-Medium.ttf").exists()),
            'zh',
            'en'
        )


    _app = TmpApp(tk.Tk())
    window = TranslationWindow(_app)
    show()
    # threading.Thread(target=lambda: (time.sleep(5), _app.root.destroy())).start()
    _app.root.mainloop()
