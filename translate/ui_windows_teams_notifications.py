#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_windows_teams_notifications.py
@Author     : LeeCQ
@Date-Time  : 2026/1/19 02:07
"""
import logging
import queue
import threading
from datetime import datetime
from tkinter import messagebox
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk

from PIL import ImageTk

from translate import DEBUGGER
from translate.other_tools.monitor_teams_notification import NotificationMonitor, Screenshot

help_message = """
1. 配置坐标
   - 点击"配置坐标"按钮
   - 在配置窗口中，参考图标示例选择合适的区域
   - 点击"选择活动/团队/聊天图标区域"按钮
   - 在Teams应用中拖动鼠标选择图标区域（请参考示例图片选择包含红色通知点的完整图标区域）
   - 选择完成后松开鼠标确认，ESC键或右键取消选择
   - 点击"保存配置"保存坐标信息

2. 选择音频文件
   - 点击"设置"菜单中的"选择音频文件"
   - 选择一个WAV或MP3格式的音频文件作为提醒铃声

3. 开始监控
   - 确保Teams应用已打开且图标位置与配置的坐标匹配
   - 点击"开始监控"按钮
   - 当检测到Teams图标上的红色通知气泡时，将播放提醒铃声

4. 停止监控
   - 点击"停止监控"按钮停止监控

5. 检测频率设置
   - 可以在界面上调整检测间隔（秒），默认为60秒
   - 点击"保存"按钮保存设置

6. 停止播放提醒
   - 当有通知提醒时，可以点击"已收到通知，停止播放"按钮来停止当前的提醒铃声

注意事项：
- 需要确保Teams应用窗口始终可见
- 坐标配置需要根据实际屏幕分辨率和Teams界面调整
- 选择图标区域时，请参考配置窗口中的示例图片，确保包含红色通知点区域
- 提醒铃声将在通知气泡消失后自动停止
- 请保持Teams界面在最前显示，不要锁屏
- 设置电脑不要自动休眠或关机，以免影响监控效果

更新说明（2026年1月后）：
- 新增检测频率设置功能，用户可自定义监控间隔时间
- 增加了"已收到通知，停止播放"按钮，可手动停止当前提醒
- 改进了GUI日志显示，添加了滚动条以便查看历史日志
- 优化了日志显示区域，采用左右分栏布局，提高界面可用性
- 增加了音量提示标签，提醒用户保持音量在合适水平
- 改进了GUI组件的错误处理，防止在组件销毁时出现错误
- 添加了系统音量检测功能（如可用），并会在日志中提示当前音量水平
- 优化了监控器与GUI之间的交互，使用更安全的线程更新机制
- 修复了在某些情况下GUI组件更新失败的问题
- 增强了程序的稳定性，改进了异常处理机制"""

about_message = """
Teams通知监控器 v1.0

此应用程序用于监控Microsoft Teams应用的通知，
当检测到活动、团队或聊天图标上的红色通知气泡时，
会播放自定义的提醒铃声。

开发目的：帮助用户及时注意到Teams通知，
特别是当有多个应用窗口或通知图标被遮挡时。

作者：Johncao@gtjas.com.hk
"""

logger = logging.getLogger("translate.ui.teams_notifications_listener_window")


class GUIHandler(logging.Handler):
    def __init__(self, queue_: queue.Queue):
        super().__init__()
        self.queue_ = queue_

    def emit(self, record: logging.LogRecord):
        if self.queue_.full():
            self.queue_.get()
        self.queue_.put(self.format(record))


class TeamsNotificationsListenerWindow:

    def __init__(self, app):
        self.app = app

        self.window = None
        self.status_label = None
        self.logs_label = None
        self.logs_text = None
        self.screenshot_frames = []  # 存储截图展示的框架

        self.queue_logs = queue.Queue(maxsize=10)
        self.update_gui_logs_thread = threading.Thread(target=self.update_gui_logs, daemon=True)
        self.update_gui_logs_thread.start()
        self.gui_handler = GUIHandler(self.queue_logs)
        self.gui_handler.setLevel(logging.DEBUG if DEBUGGER else logging.INFO)
        self.gui_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.gui_logger = {
            "translate.ui.teams_notifications_listener_window",
            "translate.monitor_teams_notification",
            "translate.keepalive"
        }
        for _ln in self.gui_logger:
            logging.getLogger(_ln).addHandler(self.gui_handler)

        self.monitor: NotificationMonitor | None = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("exit TeamsNotificationsListenerWindow")
        self.stop()
        self.queue_logs = None
        for _ln in self.gui_logger:
            logger.debug(f"remove handler {self.gui_handler} from logger {_ln}")
            logging.getLogger(_ln).removeHandler(self.gui_handler)

    def update_gui_logs(self):
        """从队列中获取日志并更新到GUI"""
        while True:
            if self.queue_logs is None:
                break
            log_text = self.queue_logs.get()
            self.add_log(log_text)

    def add_log(self, log_text):
        """添加运行日志"""
        if not self.logs_text:
            return
        try:
            self.logs_text.insert(tk.END, log_text + "\n")
            # 自动滚动到最新日志
            self.logs_text.see(tk.END)
        except tk.TclError:
            pass

    def start(self):
        """开始监控"""
        logger.info("初始化监控线程 ...")
        if self.monitor:
            self.monitor.stop()
        self.monitor = NotificationMonitor(self.app)
        logger.debug(f"monitor status: {self.monitor.status_notify}")

        self.app.keepalive.start()  # 确保系统保持运行
        self.window.attributes("-topmost", False)
        messagebox.showinfo("提示", "1.确保音量已经调整到合适的大小\n2.确保Teams应用窗口始终可见")
        self.window.attributes("-topmost", True)
        self.monitor.start()

        self.status_label.config(text="监控中", bg="#28a745", fg="white")  # 更新状态标签：绿底白字，居中显示
        self.update_screenshots()  # 更新截图线程
        logger.info(f"监控已启动")

    def stop(self):
        """关闭监控"""
        logger.info("正在停止监控 ...")
        if self.monitor:
            self.monitor.stop()
            self.monitor = None

        self.status_label.config(text="已停止", bg="#7D7D7E", fg="white")  # 更新状态标签：深灰色底白字，居中显示
        self.window.attributes("-topmost", False)
        messagebox.showinfo("提示", "监控已停止，窗口即将关闭")
        self.window.destroy()
        self.window = None
        if hasattr(self.app, "debug__") and self.app.debug__:
            self.app.root.destroy()

    def show_settings(self):
        """显示设置窗口"""

        def callback():
            if self.window:
                logger.info("窗口重新置顶")
                self.window.attributes("-topmost", True)  # 窗口置顶

        self.window.attributes("-topmost", False)  # 窗口取消置顶
        return self.app.root.after(100, self.app.settings_window.show, callback)

    def update_screenshots(self):
        """更新截图展示区（模拟）"""

        # noinspection PyTypeChecker
        def _update(screenshots: list[Screenshot]):
            # 清空原有截图
            logger.debug(f"update screenshots, {len(screenshots)} screenshots")
            for frame in self.screenshot_frames:
                for widget in frame.winfo_children():
                    widget.destroy()

            # 添加新截图
            for i, scr in enumerate(screenshots):
                # 截图时间标签
                logger.debug(f"add screenshot {i}, {scr.datetime}, {scr.name}")
                time_label = tk.Label(self.screenshot_frames[i], text=scr.datetime, font=("Arial", 8))
                time_label.pack(pady=2)
                name_label = tk.Label(self.screenshot_frames[i], text=scr.name, font=("Arial", 8))
                name_label.pack(pady=2)

                # 模拟截图（20x20的彩色方块，实际使用时替换为PhotoImage）
                # 创建一个随机颜色的画布模拟截图
                tk_image = ImageTk.PhotoImage(scr.image)
                image_label = tk.Label(self.screenshot_frames[i], image=tk_image)
                image_label.pack()
                self.screenshot_frames[i].image = tk_image

        def _update_screenshots():
            logger.info("截图更新线程screenshots在线程中开始 ...")
            while self.monitor:
                try:
                    _update(self.monitor.queue_screenshots.get(timeout=2))
                except (tk.TclError, queue.Empty):
                    pass
                if self.monitor:
                    if self.monitor.status_notify:
                        self.status_label.config(text="告警中", bg="#FF4500", fg="white")
                    else:
                        self.status_label.config(text="监控中", bg="#28a745", fg="white")
            logger.info("截图更新线程screenshots已结束 ...")

        threading.Thread(target=_update_screenshots, daemon=True).start()

    def show(self):
        if self.window:
            messagebox.showwarning("Teams监控已经启用", "不能重复启用")
            return

        x = (self.app.root.winfo_screenwidth() - 700) // 2
        y = (self.app.root.winfo_screenheight() - 600) // 2

        # 创建主窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("Teams监控")
        # 取消无边框（方便操作，如需保留可取消注释）
        # self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)  # 窗口置顶
        self.window.geometry(f"700x600+{x}+{y}")
        self.window.resizable(True, True)
        self.window.protocol("WM_DELETE_WINDOW", self.stop)

        # 主容器
        main_container = ttk.Frame(self.window, padding="10")
        main_container.pack(fill="both", expand=True)

        # ========== 第一行：按钮区 ==========
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill="x", pady=(0, 10))

        # 三个按钮，水平排列，均匀分布
        ttk.Button(button_frame, text="开始监控", command=self.start).pack(side="left", padx=5, expand=True)
        ttk.Button(button_frame, text="停止监控", command=self.stop).pack(side="left", padx=5, expand=True)
        ttk.Button(button_frame, text="设置", command=self.show_settings).pack(side="left", padx=5, expand=True)

        # ========== 第二行：状态横幅 ==========
        self.status_label = tk.Label(
            main_container,
            text="已停止",
            bg="#7D7D7E",  # 默认红色背景（未监控）
            fg="white",
            font=("Arial", 12, "bold"),
            height=2  # 增加高度，做成横幅效果
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        # ========== 第三行：截图展示区 ==========
        screenshot_frame = ttk.LabelFrame(main_container, text="截图内容")
        screenshot_frame.pack(fill="x", pady=(0, 10))

        # 创建4个截图展示框
        for i in range(4):
            frame = ttk.Frame(screenshot_frame)
            frame.pack(side="left", padx=10, pady=5, expand=True)
            self.screenshot_frames.append(frame)

        # ========== 第四行：运行日志区 ==========
        log_frame = ttk.LabelFrame(main_container, text="运行日志")
        log_frame.pack(fill="both", expand=True, pady=(0, 10))

        # 带滚动条的文本框
        self.logs_text = scrolledtext.ScrolledText(
            log_frame,
            wrap="word",
            font=("Consolas", 9)
        )
        self.logs_text.pack(fill="both", expand=True, padx=5, pady=5)
        # 初始日志
        self.add_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 程序已启动")

        # ========== 第五行：链接行 ==========
        link_frame = ttk.Frame(main_container)
        link_frame.pack(fill="x", anchor="center")

        # 帮助链接
        help_link = ttk.Label(link_frame, text="帮助", foreground="#007bff", cursor="hand2")
        help_link.pack(side="left", padx=20)
        help_link.bind("<Button-1>", lambda e: self.open_help())
        # 分隔符
        # ttk.Label(link_frame, text="|").pack(side="left")
        # # 关于链接
        # about_link = ttk.Label(link_frame, text="关于", foreground="#007bff", cursor="hand2")
        # about_link.pack(side="left", padx=20)
        # about_link.bind("<Button-1>", lambda e: self.open_about())

    def open_help(self):
        self.window.attributes("-topmost", False)  # 窗口置顶
        messagebox.showinfo("帮助", help_message)
        self.window.attributes("-topmost", True)  # 窗口置顶


if __name__ == '__main__':
    class _APP:
        def __init__(self):
            self.debug__ = True
            self.root = tk.Tk()
            self.root.withdraw()  # 隐藏主窗口


    logging.basicConfig(level=logging.DEBUG)
    logging.debug("程序启动")

    _app = _APP()
    _app.root.after(0, TeamsNotificationsListenerWindow(_app).show)
    _app.root.mainloop()
