#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_settings.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:05
"""

import tkinter as tk
from tkinter import ttk, messagebox


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.hotkey_entry = None
        self.source_lang_combobox = None
        self.target_lang_combobox = None

        # 支持的语言列表（简化版）
        self.languages = {
            "auto": "自动检测",
            "zh-CN": "中文",
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语"
        }

    def show(self):
        """显示设置窗口"""
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("应用设置")
        self.window.geometry("400x300")
        self.window.resizable(False, False)

        # 创建布局
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 全局快捷键设置
        ttk.Label(frame, text="全局翻译快捷键:").pack(anchor=tk.W, pady=(10, 5))
        self.hotkey_entry = ttk.Entry(frame)
        self.hotkey_entry.pack(fill=tk.X, pady=(0, 15))
        self.hotkey_entry.insert(0, self.app.config.hotkey)
        ttk.Label(frame, text="提示: 格式如 '<ctrl>+<alt>+t'", foreground="gray").pack(anchor=tk.W, pady=(0, 10))

        # 源语言设置
        ttk.Label(frame, text="默认源语言:").pack(anchor=tk.W, pady=(10, 5))
        self.source_lang_combobox = ttk.Combobox(frame, values=list(self.languages.values()))
        self.source_lang_combobox.pack(fill=tk.X, pady=(0, 15))
        # 查找当前源语言对应的显示文本
        source_lang_name = self.languages.get(self.app.config.source_lang, "自动检测")
        self.source_lang_combobox.current(list(self.languages.values()).index(source_lang_name))

        # 目标语言设置
        ttk.Label(frame, text="默认目标语言:").pack(anchor=tk.W, pady=(10, 5))
        self.target_lang_combobox = ttk.Combobox(frame, values=list(self.languages.values()))
        self.target_lang_combobox.pack(fill=tk.X, pady=(0, 15))
        # 查找当前目标语言对应的显示文本
        target_lang_name = self.languages.get(self.app.config.target_lang, "中文")
        self.target_lang_combobox.current(list(self.languages.values()).index(target_lang_name))

        # 按钮区域
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)

        save_button = ttk.Button(button_frame, text="保存设置", command=self.save_settings)
        save_button.pack(side=tk.RIGHT, padx=5)

    def save_settings(self):
        """保存设置"""
        # 获取用户输入
        new_hotkey = self.hotkey_entry.get().strip()
        source_lang_name = self.source_lang_combobox.get()
        target_lang_name = self.target_lang_combobox.get()

        # 验证快捷键格式（简单验证）
        if not new_hotkey:
            messagebox.showerror("错误", "请输入快捷键")
            return

        # 转换语言名称为代码
        source_lang_code = next(key for key, value in self.languages.items() if value == source_lang_name)
        target_lang_code = next(key for key, value in self.languages.items() if value == target_lang_name)

        # 更新配置
        self.app.config.hotkey = new_hotkey
        self.app.config.source_lang = source_lang_code
        self.app.config.target_lang = target_lang_code
        self.app.config.save_settings()

        # 更新快捷键
        self.app.hotkey_listener.update_hotkey(new_hotkey)

        messagebox.showinfo("成功", "设置已保存")
        self.window.destroy()
