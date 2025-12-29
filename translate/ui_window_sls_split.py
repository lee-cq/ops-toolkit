#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_sls_split.py
@Author     : LeeCQ
@Date-Time  : 2025/12/28 05:21

日志下载切割窗口
"""
import logging
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter import messagebox

from translate.other_tools.aliyun_sls_split import LogSplit

logger = logging.getLogger("translate.ui.window_sls_split")
default_workdir = Path(os.environ.get("USERPROFILE")).joinpath("Downloads", "aliyun_sls_download")


class SlsSplitWindow:

    def __init__(self, app, uri):
        self.app = app
        self.uri = uri

        self.window = None
        self.log_split = None
        # 控件变量
        self.uri_var = None
        self.workdir_var = None
        self.split_by_path_var = None
        self.split_by_hostname_var = None
        self.remove_date_var = None
        self.single_file_var = None
        self.logs_text = None

    def show(self):
        """展示日志下载切割窗口

        需要如下控件，
        URI, 输入框，默认值：self.uri， 第一行
        Workdir, 输入框，默认值: ""， 第二行
        按Path拆分文件, 复选框。默认值：True，第三行，平均分布
        按主机名拆分文件, 复选框。默认值：False，第三行，平均分布
        拆分前移除Path中的日期，复选框，默认值：True，第三行，平均分布
        输出到单个文件， 复选框， 默认值：False，第三行，平均分布
        确认，按钮，绑定方法，self.run()， 第四行，居中
        分割线
        日志显示文本框， 第五行， 平均分布


        :return:
        """
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("日志下载切割")
        self.window.geometry("600x500")
        self.window.resizable(True, True)

        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(1, weight=1)

        # 第一行：URI输入框
        ttk.Label(main_frame, text="URI:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5), padx=(0, 10))
        self.uri_var = tk.StringVar(value=self.uri)
        uri_entry = ttk.Entry(main_frame, textvariable=self.uri_var)
        uri_entry.grid(row=0, column=1, sticky=tk.EW, pady=(10, 5), columnspan=2)

        # 第二行：Workdir输入框
        ttk.Label(main_frame, text="Workdir:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5), padx=(0, 10))
        self.workdir_var = tk.StringVar(value=str(
            Path(os.environ.get("USERPROFILE")).joinpath("Downloads", "aliyun_sls_download")
        ))
        workdir_entry = ttk.Entry(main_frame, textvariable=self.workdir_var)
        workdir_entry.grid(row=1, column=1, sticky=tk.EW, pady=(10, 5), columnspan=2)

        # 第三行：三个复选框，平均分布
        check_frame = ttk.Frame(main_frame)
        check_frame.grid(row=2, column=0, columnspan=3, pady=(10, 15))
        check_frame.columnconfigure(0, weight=1)
        check_frame.columnconfigure(1, weight=1)
        check_frame.columnconfigure(2, weight=1)

        # 按Path拆分文件复选框
        self.split_by_path_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(check_frame, text="按Path拆分文件", variable=self.split_by_path_var).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))

        # 按Hostname拆分文件复选框
        self.split_by_hostname_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_frame, text="按Hostname拆分文件", variable=self.split_by_hostname_var).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 10))

        # 拆分前移除Path中的日期复选框
        self.remove_date_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(check_frame, text="移除Path中的日期", variable=self.remove_date_var).grid(
            row=0, column=2, sticky=tk.W, padx=(0, 10))

        # 输出到单个文件复选框
        self.single_file_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_frame, text="输出到单个文件", variable=self.single_file_var).grid(
            row=0, column=3, sticky=tk.W)

        # 第四行：确认按钮，居中
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        button_frame.columnconfigure(0, weight=1)

        confirm_button = ttk.Button(button_frame, text="确认", command=self.run)
        confirm_button.grid(row=0, column=0, padx=10, pady=10)
        open_button = ttk.Button(button_frame, text="打开文件夹", command=self.open_logdir)
        open_button.grid(row=0, column=1, padx=10, pady=10)

        # 第五行：日志显示文本框，带滚动条
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky=tk.NSEW)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        # 创建垂直滚动条
        self.logs_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
        self.logs_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        # 创建文本框并关联滚动条
        self.logs_text = tk.Text(
            log_frame,
            wrap="word",
            yscrollcommand=self.logs_scrollbar.set,
            state=tk.DISABLED  # 默认禁用编辑功能
        )
        self.logs_text.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 5))

        # 配置滚动条
        self.logs_scrollbar.config(command=self.logs_text.yview)

        # 确保主框架的第4行能够扩展
        main_frame.rowconfigure(4, weight=1)

    def add_log(self, message):
        """向日志文本框中添加一条日志信息

        Args:
            message: 要添加的日志消息
        """
        if self.logs_text:
            self.logs_text.config(state=tk.NORMAL)
            self.logs_text.insert(tk.END, message + "\n")
            self.logs_text.config(state=tk.DISABLED)
            # 自动滚动到底部
            self.logs_text.see(tk.END)
            # 刷新界面
            self.window.update_idletasks()

    def run(self):
        """执行日志下载切割操作

        需要实现具体的切割逻辑，这里仅作为示例
        """
        if self.log_split:
            messagebox.showwarning("警告", "切割线程已在运行，无法重复启动")
            return

        # 获取用户输入的值
        uri = self.uri_var.get()
        workdir = self.workdir_var.get()
        split_by_path = self.split_by_path_var.get()
        split_by_hostname = self.split_by_hostname_var.get()
        remove_date = self.remove_date_var.get()
        single_file = self.single_file_var.get()

        # 检查必填项
        if not uri or not workdir:
            messagebox.showwarning("警告", "请输入URI和Workdir")
            return

        try:
            self.log_split = LogSplit(
                uri=uri,
                workdir=workdir,
                diff_path=split_by_path,
                diff_hostname=split_by_hostname,
                remove_path_num=remove_date,
                single_file=single_file,
            )
            threading.Thread(target=self.log_split.start, daemon=True).start()
        except Exception as _e:
            messagebox.showerror("SLS错误", str(_e))
            self.log_split = None
            logger.error("SLS错误", exc_info=True)
            return

        while self.is_running():
            self.add_log(self.log_split.gui_logs.get())
            time.sleep(0.5)

        start_wait = time.time()
        while time.time() - start_wait < 3:
            try:
                self.add_log(self.log_split.gui_logs.get(timeout=2))
            except queue.Empty:
                pass

        if self.log_split.status == "error":
            messagebox.showerror("SLS错误", "日志文件处理错误.")
            self.log_split = None
            return

    def is_running(self):
        if self.window is None:
            return False
        if self.log_split is None:
            return False
        if self.log_split.status in ["done", "error"]:
            return False
        if not self.window.winfo_exists():
            return False
        return True

    def open_logdir(self):
        if self.log_split is None:
            os.system(f"explorer \"{self.workdir_var.get()}\"")
            return

        os.system(f'explorer "{self.log_split.workdir}"')


if __name__ == '__main__':
    class App:
        def __init__(self):
            self.root = tk.Tk()


    logging.basicConfig(level=logging.DEBUG)
    _app = App()

    s = SlsSplitWindow(_app, "test")
    s.show()

    _app.root.mainloop()
