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
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import messagebox

from ops_toolkit import DEBUGGER
from ops_toolkit.aliyun_sls.aliyun_sls_split import LogSplit, mapping_access_env
from ops_toolkit.log import GUIHandler

logger = logging.getLogger("ops_toolkit.sls_split.ui")
default_workdir = Path(os.environ.get("USERPROFILE", "\\")).joinpath("Downloads", "aliyun_sls_download")


class SlsSplitWindow:

    def __init__(self, app, uri=""):
        self.app = app
        self.uri = uri

        self.window = None
        self.log_split = None
        self.notebook = None
        self.logs_text_list: list[scrolledtext.ScrolledText] = []  # 存储所有日志文本框的列表

        self.queue_logs = queue.Queue(maxsize=10)
        self.update_gui_logs_thread = threading.Thread(target=self.update_gui_logs, daemon=True)
        self.update_gui_logs_thread.start()
        self.gui_handler = GUIHandler(self.queue_logs)
        self.gui_handler.setLevel(logging.DEBUG if DEBUGGER else logging.INFO)
        self.gui_logger = (
            "ops_toolkit.sls_split",
        )
        for _ln in self.gui_logger:
            logging.getLogger(_ln).addHandler(self.gui_handler)

        # 共享的 SLS 信息变量
        self.workdir_var = tk.StringVar(value=str(default_workdir))
        self.sls_entries = {
            "diff_path": ("📁 按Path拆分文件", tk.BooleanVar(value=True)),
            "diff_hostname": ("🖥️ 按Hostname拆分文件", tk.BooleanVar(value=True)),
            "remove_path_num": ("📅 移除Path中的日期", tk.BooleanVar(value=True)),
            "single_file": ("📄 输出到单个文件", tk.BooleanVar(value=True)),
            "single_file_add_prefix": ("🏷️ 单文件时添加前缀", tk.BooleanVar(value=True)),
        }

        # URL 和 SDK 专用变量
        self.uri_var = None
        self.query_entries = {}
        self.access_entries = {}
        self.logs_text = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("exit Aliyun SLS log Download")
        self.queue_logs = None
        for _ln in self.gui_logger:
            logger.debug(f"remove handler {self.gui_handler} from logger {_ln}")
            logging.getLogger(_ln).removeHandler(self.gui_handler)

    def update_gui_logs(self):
        """从队列中获取日志并更新到GUI"""
        while True:
            if self.queue_logs is None:
                break
            try:
                log_text = self.queue_logs.get(timeout=3)
                self.add_log(log_text)
            except queue.Empty:
                time.sleep(0.1)

    def show(self, window=None):
        """展示日志下载切割窗口"""
        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = window or tk.Toplevel(self.app.root)
        self.window.title("Aliyun日志下载&分割")
        self.window.geometry("900x750")
        self.window.resizable(True, True)
        self.window.minsize(800, 600)

        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 创建标签页控件
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)

        self.show_url_tab()
        self.show_sdk_tab()
        self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 程序已启动，选择合适的标签页开始操作")

    def show_url_tab(self):
        """展示URL选项卡"""
        url_frame = ttk.Frame(self.notebook)
        self.notebook.add(url_frame, text="🔗 URL下载")

        # 创建主框架
        main_frame = ttk.Frame(url_frame, padding="10")
        main_frame.pack(fill="both", expand=True)

        # URI 输入区域
        uri_frame = ttk.LabelFrame(main_frame, text="📥 URI", padding=10)
        uri_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(uri_frame, text="日志URI:", font=("微软雅黑", 10)).pack(side="left", padx=5)
        help_link = ttk.Label(uri_frame, text='如何获取？', font=("微软雅黑", 7), foreground="#007bff", cursor="hand2")
        help_link.pack(side="left", padx=5)
        ToolTip(help_link, img_path='url')
        # help_link.bind("<Button-1>", lambda e: self.open_help("url"))

        self.uri_var = tk.StringVar(value=self.uri)
        uri_entry = ttk.Entry(uri_frame, textvariable=self.uri_var, font=("Consolas", 10))
        uri_entry.pack(fill="x", pady=(5, 0))

        # SLS 信息区域（共享）
        self.create_shared_sls_info(main_frame, self.run_url)

    def show_sdk_tab(self):
        """展示SDK选项卡"""
        sdk_frame = ttk.Frame(self.notebook)
        self.notebook.add(sdk_frame, text="🔧 SDK下载")

        # 创建主框架
        main_frame = ttk.Frame(sdk_frame, padding="10")
        main_frame.pack(fill="both", expand=True)

        # 创建左右分栏
        paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        paned_window.pack(fill="both", expand=True)

        # 左侧：Access Info
        left_frame = ttk.LabelFrame(paned_window, text="🔑 访问凭证", padding=10, width=300)
        paned_window.add(left_frame, weight=1)

        # 表单标签与输入框
        self.access_entries = {
            "cloud_account": tk.StringVar(value=os.environ.get(mapping_access_env.get("cloud_account", ""), "")),
            "access_id": tk.StringVar(value=os.environ.get(mapping_access_env.get("access_id", ""), "")),
            "access_secret": tk.StringVar(value=os.environ.get(mapping_access_env.get("access_secret", ""), "")),
            "access_token": tk.StringVar(value=os.environ.get(mapping_access_env.get("access_token", ""), "")),
        }

        for i, (label_text, var) in enumerate(self.access_entries.items()):
            ttk.Label(left_frame, text=label_text + ":", font=("微软雅黑", 9)).grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 10))
            entry = ttk.Entry(left_frame, textvariable=var, width=25, font=("Consolas", 9))
            entry.grid(row=i, column=1, pady=5, sticky="ew")

        left_frame.columnconfigure(1, weight=1)

        # 解析按钮
        help_link = ttk.Label(left_frame, text='如何获取？', font=("微软雅黑", 7), foreground="#007bff", cursor="hand2")
        help_link.grid(row=len(self.access_entries), column=0, pady=(15, 0))
        ToolTip(help_link, img_path='sdk')
        # help_link.bind("<Button-1>", lambda e: self.open_help('sdk'))
        parse_btn = ttk.Button(left_frame, text="📋 解析 Access Info",
                               command=self.parse_access_info, width=20)
        parse_btn.grid(row=len(self.access_entries), column=1, pady=(15, 0))

        # 右侧：Query Info
        right_frame = ttk.LabelFrame(paned_window, text="🔍 查询配置", padding=10)
        paned_window.add(right_frame, weight=2)

        self.query_entries = {
            "project": tk.StringVar(),
            "logstore": tk.StringVar(),
            "query": tk.StringVar(value="*"),
            "from_time": tk.StringVar(value="-15min"),
            "to_time": tk.StringVar(value="now"),
            "endpoint": tk.StringVar(value="cn-hongkong.log.aliyuncs.com"),
        }

        query_labels = {
            "project": "项目名称",
            "logstore": "日志库名",
            "query": "查询语句",
            "from_time": "开始时间 ?",
            "to_time": "结束时间 ?",
            "endpoint": "接入点"
        }

        for i, (key, var) in enumerate(self.query_entries.items()):
            title = ttk.Label(right_frame, text=query_labels[key] + ":", font=("微软雅黑", 9))
            title.grid(row=i, column=0, sticky="w", pady=5, padx=(0, 10))
            entry = ttk.Entry(right_frame, textvariable=var, font=("Consolas", 9))
            entry.grid(row=i, column=1, pady=5, sticky="ew", padx=(0, 10))

            # 为时间字段添加提示
            if key in ["from_time", "to_time"]:
                ToolTip(title, text="格式: now, -15min, 2024-01-01")
                # ttk.Label(right_frame, text="格式: now, -15min, 2024-01-01",
                #           font=("微软雅黑", 8), foreground="gray").grid(
                #     row=i, column=2, sticky="w", pady=5)

        right_frame.columnconfigure(1, weight=1)

        # SLS 信息区域（共享）
        self.create_shared_sls_info(main_frame, self.run_sdk)

    def create_shared_sls_info(self, parent_frame, callback):
        """创建共享的 SLS 信息区域"""
        # 工作目录设置
        workdir_frame = ttk.LabelFrame(parent_frame, text="📂 输出配置", padding=10)
        workdir_frame.pack(fill="x", pady=(10, 5))

        workdir_inner = ttk.Frame(workdir_frame)
        workdir_inner.pack(fill="x")

        ttk.Label(workdir_inner, text="工作目录:", font=("微软雅黑", 10)).pack(side="left")
        workdir_entry = ttk.Entry(workdir_inner, textvariable=self.workdir_var,
                                  font=("Consolas", 9))
        workdir_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # 选项设置
        options_frame = ttk.LabelFrame(parent_frame, text="⚙️ 处理选项", padding=10)
        options_frame.pack(fill="x", pady=(0, 10))

        # 创建选项网格
        opts_container = ttk.Frame(options_frame)
        opts_container.pack(fill="x")

        for i, (text, var) in enumerate(self.sls_entries.values()):
            cb = ttk.Checkbutton(opts_container, text=text, variable=var, style="Toolbutton")
            cb.pack(side="left", padx=10, pady=5)  #

        # 操作按钮
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill="x", pady=(0, 10))

        confirm_btn = ttk.Button(button_frame, text="🚀 开始处理",
                                 command=callback, style="Accent.TButton")
        confirm_btn.pack(side="left", padx=(0, 10))

        open_dir_btn = ttk.Button(button_frame, text="📂 打开目录",
                                  command=self.open_logdir)
        open_dir_btn.pack(side="left", padx=(0, 10))

        ttk.Separator(parent_frame, orient="horizontal").pack(fill="x", pady=5)

        # 日志显示区域
        log_frame = ttk.LabelFrame(parent_frame, text="📋 运行日志", padding=5)
        log_frame.pack(fill="both", expand=True)

        # 带滚动条的文本框
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill="both", expand=True)

        # 为每个标签页创建独立的日志文本框
        logs_text = scrolledtext.ScrolledText(
            log_container,
            wrap="word",
            font=("Consolas", 9),
            height=12
        )
        logs_text.pack(fill="both", expand=True)
        self.logs_text_list.append(logs_text)  # 添加到列表中以便同步

        # 添加清空日志按钮
        clear_btn = ttk.Button(
            log_frame, text="🗑️清空日志",
            command=lambda: [(_logs.config(state="normal"), _logs.delete(1.0, tk.END)) for _logs in self.logs_text_list]
        )
        clear_btn.pack(side="right", pady=(5, 0))

    def parse_access_info(self):
        """解析Access Info表单中的信息"""

        def callback():
            # 获取输入的文本内容
            input_text = acc_info_text.get("1.0", tk.END).strip()

            # 定义关键词映射关系
            key_mapping = {
                "云账号": "cloud_account",
                "权限": "access_secret",
                "AccessKey ID": "access_id",
                "AccessKey Secret": "access_secret",
                "SecurityToken": "access_token"
            }

            # 解析文本内容
            parsed_data = {}
            lines = input_text.split('\n')

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line in key_mapping:
                    # 找到对应的值（通常是下一行）
                    if i + 1 < len(lines):
                        value_line = lines[i + 1].strip()
                        # 移除可能的"复制"字样
                        if value_line.endswith("复制"):
                            value_line = value_line[:-2]
                        parsed_data[key_mapping[line]] = value_line
                        i += 2  # 跳过值行
                    else:
                        i += 1
                else:
                    i += 1

            # 更新表单字段
            for key, var in self.access_entries.items():
                if key in parsed_data:
                    var.set(parsed_data[key])

            new_window.destroy()
            logger.info("解析Access Info成功")
            self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Access Info解析完成")

        new_window = tk.Toplevel(self.window)
        new_window.title("解析Access Info")
        new_window.geometry("450x350")
        new_window.resizable(True, True)
        # 窗口置顶
        new_window.attributes("-topmost", True)

        # 添加说明标签
        ttk.Label(new_window, text="请粘贴Access信息文本:",
                  font=("微软雅黑", 10, "bold")).pack(pady=(15, 5))

        # 文本输入框
        text_frame = ttk.Frame(new_window, padding=10)
        text_frame.pack(fill="both", expand=True, padx=10)

        acc_info_text = tk.Text(text_frame, height=12, width=50,
                                font=("Consolas", 9), wrap="word")
        acc_info_text.pack(fill="both", expand=True)

        # 按钮区域
        button_frame = ttk.Frame(new_window, padding=10)
        button_frame.pack(fill="x")

        # 解析按钮
        parse_btn = ttk.Button(button_frame, text="✅ 解析",
                               command=callback, style="Accent.TButton")
        parse_btn.pack(side="left", padx=(0, 10))

        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="❌ 取消",
                                command=new_window.destroy)
        cancel_btn.pack(side="left")

    def add_log(self, message: str):
        """向所有日志文本框中添加一条日志信息

        Args:
            message: 要添加的日志消息
        """
        _line_msg = f">>> 已处理 {self.log_split.total_line}" if self.log_split else ""
        for logs_text in self.logs_text_list:
            if logs_text:
                logs_text.config(state="normal")
                if _line_msg and logs_text.get("end-1l", "end-1c").startswith(">>>"):
                    logs_text.delete("end-1l", "end")
                logs_text.insert(tk.END, "\n" + message)
                if _line_msg:
                    logs_text.insert(tk.END, "\n" + _line_msg)
                logs_text.config(state="disabled")
                logs_text.see(tk.END)
        if self.window:
            self.window.update_idletasks()  # 刷新界面

    def run_url(self):
        """执行URL日志下载切割操作"""
        if self.log_split:
            messagebox.showwarning("警告", "线程已在运行，无法重复启动")
            return

        # 获取用户输入的值
        uri = self.uri_var.get().strip()
        workdir = self.workdir_var.get().strip()
        options = {k: var[1].get() for k, var in self.sls_entries.items()}

        # 检查必填项
        if not uri:
            messagebox.showwarning("警告", "请输入日志URI")
            return
        if not workdir:
            messagebox.showwarning("警告", "请输入工作目录")
            return

        try:
            self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始处理URL日志: {uri}")

            self.log_split = LogSplit(workdir=workdir, **options)
            threading.Thread(target=self.log_split.from_uri, daemon=True, args=(uri,)).start()
        except Exception as _e:
            messagebox.showerror("SLS错误", str(_e))
            self.log_split = None
            logger.error("SLS错误", exc_info=True)
            return

        # 监控处理进度
        self.monitor_processing()

    def run_sdk(self):
        """执行SDK日志下载操作"""
        if self.log_split:
            messagebox.showwarning("警告", "线程已在运行，无法重复启动")
            return

        # 获取用户输入的值
        workdir = self.workdir_var.get().strip()
        options = {k: var[1].get() for k, var in self.sls_entries.items()}

        # 获取Access Info
        access_info = {}
        for k, var in self.access_entries.items():
            value = var.get().strip()
            if value:
                access_info[k] = value
                os.environ[mapping_access_env.get(k, "")] = value

        # 获取Query Info
        query_info = {}
        for k, var in self.query_entries.items():
            value = var.get().strip()
            if value:
                query_info[k] = value

        # 检查必填项
        required_fields = ["project", "logstore"]
        missing_fields = [field for field in required_fields if not query_info.get(field)]
        if missing_fields:
            messagebox.showwarning("警告", f"请填写必需字段: {', '.join(missing_fields)}")
            return

        if not workdir:
            messagebox.showwarning("警告", "请输入工作目录")
            return

        try:
            self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始SDK日志下载")
            self.add_log(f"项目: {query_info.get('project')}, 日志库: {query_info.get('logstore')}")

            self.log_split = LogSplit(workdir=workdir, **options)
            threading.Thread(target=self.log_split.from_sdk,
                             daemon=True,
                             kwargs=query_info
                             ).start()
        except Exception as _e:
            messagebox.showerror("SLS错误", str(_e))
            self.log_split = None
            logger.error("SLS错误", exc_info=True)
            return

        # 监控处理进度
        self.monitor_processing()

    def monitor_processing(self):
        """监控日志处理进度"""

        def check_status():
            while self.is_running():
                try:
                    # 尝试获取日志消息
                    log_msg = self.log_split.gui_logs.get_nowait()
                    self.add_log(log_msg)
                except queue.Empty:
                    pass
                time.sleep(0.1)

            # 处理完成后检查最终状态
            if self.log_split and self.log_split.status == "error":
                messagebox.showerror("SLS错误", "日志文件处理错误.")
                self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 处理失败")
            else:
                self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 处理完成")

            self.log_split = None

        # 启动监控线程
        threading.Thread(target=check_status, daemon=True).start()

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
        """打开日志目录"""
        workdir = self.workdir_var.get()

        if self.log_split and self.log_split.workdir.exists():
            webbrowser.open(self.log_split.workdir.as_posix())
            # os.system(f'explorer "{self.log_split.workdir}"')
        elif workdir and Path(workdir).exists():
            webbrowser.open(workdir)
            # os.system(f'explorer "{workdir}"')
        else:
            messagebox.showinfo("提示", "目录不存在")


class ToolTip:
    """自定义ToolTip类，实现鼠标悬停提示功能"""

    def __init__(self, widget, /, img_path="", text=""):
        self.widget = widget  # 绑定的组件
        self.img_path = img_path  # 提示文字
        self.text = text
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
        if self.tooltip:
            return
        if self.img_path and self.text:
            return

        # 创建顶级临时窗口作为提示框
        self.tooltip = tk.Toplevel(self.widget)
        # 设置为无标题栏的临时窗口
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.attributes("-topmost", True)  # 窗口置顶

        # 创建提示框内容标签
        if self.text:
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

        elif self.img_path:
            image = tk.PhotoImage(
                name=self.img_path,
                file=Path(__file__).parent / f"helper_{self.img_path}.png.py"
            )
            image_label = ttk.Label(self.tooltip, image=image)
            image_label.image = image
            image_label.pack(anchor="w", expand=True, pady=(0, 10))

        # 强制更新窗口以获取实际尺寸
        self.tooltip.update_idletasks()

        # 获取 tooltip 的实际宽度和高度
        tooltip_width = self.tooltip.winfo_reqwidth()
        tooltip_height = self.tooltip.winfo_reqheight()

        # 获取屏幕尺寸
        screen_width = self.tooltip.winfo_screenwidth()
        screen_height = self.tooltip.winfo_screenheight()

        # 获取鼠标指针的位置作为默认位置
        x = self.widget.winfo_pointerx()
        y = self.widget.winfo_pointery()

        # 在鼠标位置下方添加适当的偏移，避免遮挡鼠标指针
        x = x + 15
        y = y + 15

        # 检查是否超出右边界，如果是则向左调整
        if x + tooltip_width > screen_width:
            # 向左调整，与屏幕右侧保持 20px 距离
            x = screen_width - tooltip_width - 20

        # 检查是否超出底边界，如果是则向上显示
        if y + tooltip_height > screen_height - 20:
            # 尝试显示在鼠标上方
            y = y - tooltip_height - 30
            # 如果上方也不够空间，则贴近上边界
            if y < 20:
                y = 20

        self.tooltip.wm_geometry(f"+{x}+{y}")

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


if __name__ == '__main__':
    class App:
        def __init__(self):
            self.root = tk.Tk()


    logging.basicConfig(level=logging.DEBUG)
    _app = App()

    s = SlsSplitWindow(_app, "test")
    s.show()
    # _app.root.after(1000, s.parse_access_info)

    _app.root.mainloop()
