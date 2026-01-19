#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : ui_window_settings.py
@Author     : LeeCQ
@Date-Time  : 2025/9/19 22:05
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from ops_toolkit.config import TranslateApiModel


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.notebook = None

        # 基本设置控件
        self.app_name_entry = None
        self.hotkey_entry = None
        self.startup_var = None

        # 路径设置控件
        self.config_path_entry = None
        self.data_dir_entry = None
        self.history_path_entry = None
        self.log_path_entry = None

        # API设置控件
        self.api_tree = None
        self.api_types = ["baidu", "aliyun", "tencent"]

        # 团队设置控件
        self.teams_frame = None
        self.teams_activity_entry = None
        self.teams_chat_entry = None
        self.teams_tray_entry = None
        self.teams_team_entry = None
        self.teams_interval_entry = None

    def show(self, callback_close=None):
        """显示设置窗口"""

        def on_close():
            """退出应用"""
            if callback_close and callable(callback_close):
                callback_close()
            if self.window:
                self.window.destroy()

        # 如果窗口已存在，先销毁
        if self.window:
            self.window.destroy()

        # 创建新窗口
        self.window = tk.Toplevel(self.app.root)
        self.window.title("应用设置")
        self.window.geometry("650x500")
        self.window.resizable(True, True)
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", on_close)

        # 创建标签页控件 (新增)
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # ==================== 基本设置标签页 (新增) ====================
        basic_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(basic_frame, text="基本设置")

        # 应用名称设置 (新增)
        ttk.Label(basic_frame, text="应用名称:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5))
        self.app_name_entry = ttk.Entry(basic_frame)
        self.app_name_entry.grid(row=0, column=1, sticky=tk.EW, pady=(10, 5))
        self.app_name_entry.insert(0, self.app.config.app_name)
        basic_frame.columnconfigure(1, weight=1)

        # 全局快捷键设置
        ttk.Label(basic_frame, text="全局翻译快捷键:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.hotkey_entry = ttk.Entry(basic_frame)
        self.hotkey_entry.grid(row=1, column=1, sticky=tk.EW, pady=(10, 5))
        self.hotkey_entry.insert(0, self.app.config.hotkey)
        ttk.Label(basic_frame, text="提示: 格式如 '<ctrl>+<alt>+t'", foreground="gray"). \
            grid(row=2, column=1, sticky=tk.W)

        # 开机自启 (新增)
        ttk.Label(basic_frame, text="开机自启:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        self.startup_var = tk.BooleanVar(value=self.app.config.startup)
        ttk.Checkbutton(basic_frame, variable=self.startup_var).grid(row=3, column=1, sticky=tk.W, pady=(10, 5))

        # ==================== 路径设置标签页 (新增) ====================
        path_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(path_frame, text="路径设置")
        path_frame.columnconfigure(1, weight=1)

        # 配置文件路径 (新增)
        ttk.Label(path_frame, text="配置文件路径:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5))
        self.config_path_entry = ttk.Entry(path_frame)
        self.config_path_entry.grid(row=0, column=1, sticky=tk.EW, pady=(10, 5))
        self.config_path_entry.insert(0, str(self.app.config.config_path))
        ttk.Button(path_frame, text="浏览...",
                   command=lambda: self.browse_path(self.config_path_entry, is_file=True)).grid(row=0, column=2, padx=5)

        # 数据目录 (新增)
        ttk.Label(path_frame, text="数据目录:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.data_dir_entry = ttk.Entry(path_frame)
        self.data_dir_entry.grid(row=1, column=1, sticky=tk.EW, pady=(10, 5))
        self.data_dir_entry.insert(0, str(self.app.config.data_dir))
        ttk.Button(path_frame,
                   text="浏览...",
                   command=lambda: self.browse_path(self.data_dir_entry)
                   ).grid(row=1, column=2, padx=5)

        # 翻译历史路径 (新增)
        ttk.Label(path_frame, text="翻译历史路径:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        self.history_path_entry = ttk.Entry(path_frame)
        self.history_path_entry.grid(row=2, column=1, sticky=tk.EW, pady=(10, 5))
        self.history_path_entry.insert(0, str(self.app.config.translation_history_path))
        ttk.Button(path_frame,
                   text="浏览...",
                   command=lambda: self.browse_path(self.history_path_entry, is_file=True)
                   ).grid(row=2, column=2, padx=5)

        # 日志文件路径 (新增)
        ttk.Label(path_frame, text="日志文件路径:").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        self.log_path_entry = ttk.Entry(path_frame)
        self.log_path_entry.grid(row=3, column=1, sticky=tk.EW, pady=(10, 5))
        self.log_path_entry.insert(0, str(self.app.config.log_path))
        ttk.Button(path_frame, text="浏览...",
                   command=lambda: self.browse_path(self.log_path_entry, is_file=True)).grid(row=3, column=2, padx=5)

        # ==================== API设置标签页 (新增) ====================
        api_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(api_frame, text="API设置")

        # 添加API按钮 (新增)
        add_button = ttk.Button(api_frame, text="添加API", command=self.add_api)
        add_button.pack(side="top", anchor="nw", pady=(0, 10))

        # API列表 (新增)
        columns = ("type", "user", "passkey", "text", "image")
        self.api_tree = ttk.Treeview(api_frame, columns=columns, show="headings", height=8)
        self.api_tree.heading("type", text="类型")
        self.api_tree.heading("user", text="用户")
        self.api_tree.heading("passkey", text="密钥")
        self.api_tree.heading("text", text="文本翻译")
        self.api_tree.heading("image", text="图片翻译")

        self.api_tree.column("type", width=80)
        self.api_tree.column("user", width=150)
        self.api_tree.column("passkey", width=150)
        self.api_tree.column("text", width=80)
        self.api_tree.column("image", width=80)

        # 添加滚动条 (新增)
        api_scrollbar = ttk.Scrollbar(api_frame, orient="vertical", command=self.api_tree.yview)
        self.api_tree.configure(yscrollcommand=api_scrollbar.set)

        # 放置树状图和滚动条 (新增)
        self.api_tree.pack(side="left", fill="both", expand=True)
        api_scrollbar.pack(side="right", fill="y")

        # 绑定双击事件 (新增)
        self.api_tree.bind("<Double-1>", self.edit_api)

        # 加载API数据 (新增)
        self.load_api_data()

        # ==================== Teams 监控标签页 (新增) ====================
        self.teams_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.teams_frame, text="Teams监控")
        self.teams_frame.columnconfigure(1, weight=1, minsize=300)

        ttk.Label(self.teams_frame, text="活动图标位置").grid(row=0, column=0, sticky=tk.W, pady=(10, 5))
        self.teams_activity_entry = ttk.Entry(self.teams_frame)
        self.teams_activity_entry.grid(row=0, column=1, sticky=tk.EW, pady=(10, 5))
        self.teams_activity_entry.insert(0, self.app.config.teams.activity)
        tk.Button(self.teams_frame, text="选择活动图标区域",
                  command=lambda: self.open_screen_selector('teams_activity_entry'),
                  bg="#9E9E9E", fg="white", font=("Arial", 10)).grid(row=0, column=2, padx=5)

        ttk.Label(self.teams_frame, text="消息图标位置").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        self.teams_chat_entry = ttk.Entry(self.teams_frame)
        self.teams_chat_entry.grid(row=1, column=1, sticky=tk.EW, pady=(10, 5))
        self.teams_chat_entry.insert(0, self.app.config.teams.chat)
        tk.Button(self.teams_frame, text="选择消息图标区域",
                  command=lambda: self.open_screen_selector('teams_chat_entry'),
                  bg="#9E9E9E", fg="white", font=("Arial", 10)).grid(row=1, column=2, padx=5)

        ttk.Label(self.teams_frame, text="团队图标位置").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        self.teams_team_entry = ttk.Entry(self.teams_frame)
        self.teams_team_entry.grid(row=2, column=1, sticky=tk.EW, pady=(10, 5))
        self.teams_team_entry.insert(0, self.app.config.teams.team)
        tk.Button(self.teams_frame, text="选择团队图标区域",
                  command=lambda: self.open_screen_selector('teams_team_entry'),
                  bg="#9E9E9E", fg="white", font=("Arial", 10)).grid(row=2, column=2, padx=5)

        ttk.Label(self.teams_frame, text="托盘图标位置").grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        self.teams_tray_entry = ttk.Entry(self.teams_frame)
        self.teams_tray_entry.grid(row=3, column=1, sticky=tk.EW, pady=(10, 5))
        self.teams_tray_entry.insert(0, self.app.config.teams.tray)
        tk.Button(self.teams_frame, text="选择托盘图标区域",
                  command=lambda: self.open_screen_selector('teams_tray_entry'),
                  bg="#9E9E9E", fg="white", font=("Arial", 10)).grid(row=3, column=2, padx=5)

        ttk.Label(self.teams_frame, text="检查间隔（秒）").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        self.teams_interval_entry = ttk.Entry(self.teams_frame)
        self.teams_interval_entry.grid(row=4, column=1, sticky=tk.EW, pady=(10, 5))
        self.teams_interval_entry.insert(0, str(self.app.config.teams.interval))

        # 格式说明：
        # 格式："x,y+width+height"
        # 示例："100,200+300+400" 表示从 (100,200) 开始，宽度为 300，高度为 400
        ttk.Label(self.teams_frame,
                  text="格式：XxY+width+height\n示例：\"100x200+300+400\" 表示从 (100,200) 开始，宽度为 300，高度为 400",
                  ).grid(
            row=5, column=0, columnspan=self.teams_frame.grid_size()[0], sticky='ew')

        # 按钮区域
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill="x", pady=10)

        save_button = ttk.Button(button_frame, text="保存设置", command=self.save_settings)
        save_button.pack(side="right", padx=5)

    @staticmethod
    def browse_path(entry_widget, is_file=False):
        """浏览文件或文件夹路径 (新增)"""
        current_path = entry_widget.get()
        if is_file:
            # 浏览文件
            path = filedialog.asksaveasfilename(initialfile=current_path)
        else:
            # 浏览文件夹
            path = filedialog.askdirectory(initialdir=current_path)

        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def load_api_data(self):
        """加载API数据到列表 (新增)"""
        # 清空现有数据
        for item in self.api_tree.get_children():
            self.api_tree.delete(item)

        # 添加API数据
        for api in self.app.config.apis:
            self.api_tree.insert("", tk.END, values=(
                api.api_type,
                api.auth[0],  # user
                "***",  # 隐藏真实密钥
                f"{api.text[0]}/{api.text[1]}",  # usage
                f"{api.image[0]}/{api.image[1]}"  # image
            ))

    def add_api(self):
        """添加新API (新增)"""
        self.show_api_dialog()

    def edit_api(self, _event):
        """编辑选中的API (新增)"""
        selected_item = self.api_tree.selection()
        if not selected_item:
            return

        item = selected_item[0]
        api_index = self.api_tree.index(item)
        self.show_api_dialog(api_index)

    def show_api_dialog(self, api_index=None):
        """显示API编辑对话框 (新增)"""
        dialog = tk.Toplevel(self.window)
        dialog.title("编辑API" if api_index is not None else "添加API")
        dialog.geometry("300x250")
        dialog.resizable(False, False)
        dialog.grab_set()  # 模态窗口

        # 居中显示
        dialog.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - dialog.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # API类型 (新增)
        ttk.Label(dialog, text="API类型:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5), padx=10)
        api_type_var = tk.StringVar()
        api_type_combobox = ttk.Combobox(dialog, textvariable=api_type_var, values=self.api_types, state="readonly")
        api_type_combobox.grid(row=0, column=1, sticky=tk.EW, pady=(10, 5), padx=10)
        if self.api_types:
            api_type_combobox.current(0)

        # API用户 (新增)
        ttk.Label(dialog, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5), padx=10)
        api_user_var = tk.StringVar()
        api_user_entry = ttk.Entry(dialog, textvariable=api_user_var)
        api_user_entry.grid(row=1, column=1, sticky=tk.EW, pady=(10, 5), padx=10)

        # API密钥 (新增)
        ttk.Label(dialog, text="Secret Key:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5), padx=10)
        api_passkey_var = tk.StringVar()
        api_passkey_entry = ttk.Entry(dialog, textvariable=api_passkey_var, show="*")
        api_passkey_entry.grid(row=2, column=1, sticky=tk.EW, pady=(10, 5), padx=10)

        # 如果是编辑模式，加载现有数据 (新增)
        if api_index is not None:
            api = self.app.config.apis[api_index]
            api_type_var.set(api.api_type)
            api_user_var.set(api.auth[0])
            api_passkey_var.set(api.auth[1])

        # 按钮区域 (新增)
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        def save_api():
            api_type = api_type_var.get()
            user = api_user_var.get()
            passkey = api_passkey_var.get()

            if not api_type or not user or not passkey:
                messagebox.showerror("错误", "所有字段都是必填的")
                return

            if api_index is not None:
                # 更新现有API
                self.app.config.apis[api_index].api_type = api_type
                self.app.config.apis[api_index].auth = (user, passkey)
            else:
                # 添加新API
                new_api = TranslateApiModel(
                    api_type=api_type,
                    auth=(user, passkey),

                )
                self.app.config.apis.append(new_api)

            self.load_api_data()
            dialog.destroy()

        save_btn = ttk.Button(button_frame, text="保存", command=save_api)
        save_btn.pack(side="right", padx=5)

        cancel_btn = ttk.Button(button_frame, text="取消", command=dialog.destroy)
        cancel_btn.pack(side="right", padx=5)

        dialog.columnconfigure(1, weight=1)
        dialog.wait_window()

    def save_settings(self):
        """保存设置"""
        # 获取基本设置 (修改)
        new_app_name = self.app_name_entry.get().strip()
        new_hotkey = self.hotkey_entry.get().strip()
        new_startup = self.startup_var.get()

        # 获取路径设置 (新增)
        new_config_path = Path(self.config_path_entry.get().strip())
        new_data_dir = Path(self.data_dir_entry.get().strip())
        new_history_path = Path(self.history_path_entry.get().strip())
        new_log_path = Path(self.log_path_entry.get().strip())

        # 验证输入 (修改)
        if not new_app_name:
            messagebox.showerror("错误", "应用名称不能为空")
            return

        if not new_hotkey:
            messagebox.showerror("错误", "请输入快捷键")
            return

        # 更新配置 (修改)
        self.app.config.app_name = new_app_name
        self.app.config.hotkey = new_hotkey
        self.app.config.startup = new_startup
        self.app.config.config_path = new_config_path
        self.app.config.data_dir = new_data_dir
        self.app.config.translation_history_path = new_history_path
        self.app.config.log_path = new_log_path

        if self.teams_frame and self.teams_frame.winfo_viewable():
            # 获取Teams设置 (新增)
            teams_interval = self.teams_interval_entry.get().strip()

            teams_tray = self.teams_tray_entry.get().strip()
            teams_activity = self.teams_activity_entry.get().strip()
            teams_team = self.teams_team_entry.get().strip()
            teams_message = self.teams_chat_entry.get().strip()

            _re = re.compile(r"^\d+x\d+\+\d+\+\d+$")
            for ck in [teams_activity, teams_team, teams_message, teams_tray]:
                if not _re.match(ck):
                    messagebox.showerror("错误", f"请填写正确的设置：{ck}")
                    return
            try:
                teams_interval = int(teams_interval)
            except ValueError:
                messagebox.showerror("错误", "Teams监控间隔必须是整数")
                return
            self.app.config.teams.activity = teams_activity
            self.app.config.teams.team = teams_team
            self.app.config.teams.chat = teams_message
            self.app.config.teams.tray = teams_tray
            self.app.config.teams.interval = teams_interval

        # 保存配置并更新快捷键
        self.app.config.save()
        self.app.hotkey_listener.update_hotkey(new_hotkey)

        messagebox.showinfo("成功", "设置已保存到" + str(self.app.config.config_path))
        self.window.destroy()

    def open_screen_selector(self, event_type):
        """打开屏幕选择器"""

        def callback(position):
            self.__getattribute__(event_type).insert(0, position)

        ScreenSelector(callback=callback)


class ScreenSelector:
    def __init__(self, callback):
        self.callback = callback

        # 获取屏幕尺寸
        self.screen_width, self.screen_height = self.get_screen_size()

        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.coords_label = None
        self.position = ""

        # 创建全屏透明窗口
        self.root = tk.Toplevel()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.3)
        self.root.configure(bg='gray')

        # 创建画布
        self.canvas = tk.Canvas(self.root, highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        # 绑定事件
        self.canvas.bind("<ButtonPress-1>", self.on_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.cancel_selection)  # 添加右键点击事件
        self.root.bind("<Key>", self.key_press)  # 添加键盘事件处理
        self.root.bind("<Escape>", lambda e: self.close())  # ESC键取消
        self.root.focus_set()  # 确保窗口能接收键盘事件

        # 添加提示文本
        self.canvas.create_text(
            self.screen_width // 2,
            50,
            text="拖动鼠标选择监控区域",
            fill="white",
            font=("Arial", 20, "bold"),
            tags="instruction"
        )
        # 添加实时坐标显示
        self.coords_label = self.canvas.create_text(
            100, 30,
            text="",
            fill="red",
            font=("Arial", 14, "bold"),
            anchor="nw"
        )
        # 禁用窗口管理器的关闭按钮
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

    @staticmethod
    def get_screen_size():
        """获取屏幕尺寸"""
        root = tk.Tk()
        root.withdraw()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
        return screen_width, screen_height

    def on_start(self, event):
        # 记录起始点
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        # 清除之前的矩形
        if self.rect_id:
            self.canvas.delete(self.rect_id)

        # 创建新矩形 - 使用更明显的颜色和样式
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=3, dash=(10, 5), fill='', stipple='gray50'
        )

    def on_drag(self, event):
        # 更新矩形位置
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

        width = abs(cur_x - self.start_x)
        height = abs(cur_y - self.start_y)

        # 更新实时坐标显示
        self.canvas.itemconfig(
            self.coords_label,
            text=f"当前选择: (x,y:{self.start_x},{self.start_y}) - (w,h:{width},{height})"
        )
        # self.position = f"{self.start_x}x{self.start_y}+{width}+{height}"

    def on_release(self, _event):
        # 确认选择
        if not self.rect_id:
            return

        x1, y1, x2, y2 = self.canvas.coords(self.rect_id)
        # 确保坐标顺序正确
        x = min(x1, x2)
        y = min(y1, y2)
        width = max(abs(x2 - x1), 10)
        height = max(abs(y2 - y1), 10)

        self.callback(f"{int(x)}x{int(y)}+{int(width)}+{int(height)}")
        self.close()

    def key_press(self, _event):
        """处理键盘事件"""
        if _event.keysym.lower() == 'escape':
            self.cancel_selection(_event)

    def cancel_selection(self, _event):
        """取消选择操作"""
        self.close()

    def get_position(self):
        return self.position

    def close(self):
        self.root.destroy()
