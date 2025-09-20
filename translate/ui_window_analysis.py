#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_analsis.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:07
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class WordAnalysisWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.word_listbox = None
        self.lang_combobox = None
        self.frequency_threshold = None

    def show(self):
        """显示词汇分析窗口"""
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("词汇分析")
        self.window.geometry("600x500")
        self.window.resizable(True, True)

        # 创建布局
        frame = ttk.Frame(self.window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # 语言选择
        lang_frame = ttk.Frame(frame)
        lang_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(lang_frame, text="选择语言:").pack(side=tk.LEFT, padx=(0, 10))
        self.lang_combobox = ttk.Combobox(lang_frame, values=["英语"])
        self.lang_combobox.current(0)
        self.lang_combobox.pack(side=tk.LEFT, padx=(0, 10))

        analyze_button = ttk.Button(lang_frame, text="分析词汇", command=self.analyze_words)
        analyze_button.pack(side=tk.RIGHT)

        # 词频阈值
        threshold_frame = ttk.Frame(frame)
        threshold_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(threshold_frame, text="最小词频:").pack(side=tk.LEFT, padx=(0, 10))
        self.frequency_threshold = tk.StringVar(value="1")
        ttk.Entry(threshold_frame, textvariable=self.frequency_threshold, width=5).pack(side=tk.LEFT)

        # 词汇列表
        ttk.Label(frame, text="高频词汇 (按词频排序):").pack(anchor=tk.W, pady=(10, 5))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.word_listbox = tk.Listbox(list_frame, width=50, height=15)
        self.word_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.word_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.word_listbox.configure(yscrollcommand=scrollbar.set)

        # 按钮区域
        button_frame = ttk.Frame(self.window, padding="10")
        button_frame.pack(fill=tk.X)

        export_button = ttk.Button(button_frame, text="导出单词表", command=self.export_word_list)
        export_button.pack(side=tk.LEFT, padx=5)

        # 初始分析
        self.analyze_words()

    def analyze_words(self):
        """分析词汇并显示结果"""
        # 清空列表
        self.word_listbox.delete(0, tk.END)

        # 执行分析
        self.app.analyzer.analyze_translations()

        # 获取选择的语言
        lang_name = self.lang_combobox.get()
        lang_code = "english" if lang_name == "英语" else ""

        # 显示结果
        if lang_code in self.app.analyzer.word_counts:
            try:
                min_freq = int(self.frequency_threshold.get() or 1)
                words = [(word, count) for word, count in self.app.analyzer.word_counts[lang_code].most_common() if
                         count >= min_freq]

                for i, (word, count) in enumerate(words, 1):
                    self.word_listbox.insert(tk.END, f"{i}. {word} - 出现 {count} 次")
            except ValueError:
                self.word_listbox.insert(tk.END, "请输入有效的词频阈值")

        else:
            self.word_listbox.insert(tk.END, "没有找到足够的词汇进行分析")

    def export_word_list(self):
        """导出单词表"""
        lang_name = self.lang_combobox.get()
        lang_code = "english" if lang_name == "英语" else ""

        if lang_code not in self.app.analyzer.word_counts or not self.app.analyzer.word_counts[lang_code]:
            messagebox.showinfo("提示", "没有可导出的词汇")
            return

        # 导出到用户桌面
        try:
            min_freq = int(self.frequency_threshold.get() or 1)
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            file_name = f"{lang_name}_word_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file_path = os.path.join(desktop_path, file_name)

            if self.app.analyzer.export_word_list(lang_code, file_path, min_freq):
                messagebox.showinfo("成功", f"单词表已导出到:\n{file_path}")
            else:
                messagebox.showerror("错误", "导出单词表失败")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的词频阈值")
