import signal
import sys
import threading
import time
import tkinter as tk
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
from PIL import ImageTk

from ops_toolkit import VERSION
from ops_toolkit.tools import toolkit_notify
from ops_toolkit.tools import TimerManager
from ops_toolkit.translate.history import HistoryManager
from ops_toolkit.app_hotkey import HotkeyListener
from ops_toolkit.app_tray import SystemTray
from ops_toolkit.config import config
from ops_toolkit.hourly_reminder.hourly_reminder import HourlyReminder
from ops_toolkit.monitor_clipboard.monitor_clipboard import MonitorClipboard
from ops_toolkit.translate.ui_window_history import HistoryWindow
from ops_toolkit.ui_window_log import LogWindow
from ops_toolkit.ui_window_settings import SettingsWindow
from ops_toolkit.translate.main import Translater
from ops_toolkit.monitor_clipboard.ui_window_clipboard import ClipboardWindow
from ops_toolkit.monitor_teams.ui_windows_teams_notifications import TeamsNotificationsListenerWindow
from ops_toolkit.keepalive import Keepalive
from ops_toolkit.todolist.main import TodoManager
from ops_toolkit.update_version import check_update as _check_update

if TYPE_CHECKING:
    from ops_toolkit.config import Config

logger = getLogger("ops_toolkit.app.main")


# noinspection PyTypeChecker
class App:
    def __init__(self):

        self.version = VERSION
        self.app_name = config.app_name
        self.title = f"{config.app_name} @ {VERSION}"
        # 初始化配置
        logger.info(f"APP Start @ {VERSION} ...")
        self.config: "Config" = config
        self.exit_flag = False
        self.exited = False

        # 初始化GUI
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏主窗口

        _img = Image.open(Path(__file__).parent.joinpath("resources/app-icon.png.py").open("rb"))
        self.img = ImageTk.PhotoImage(_img)
        # noinspection PyTypeChecker
        self.root.iconphoto(True, self.img)

        # 初始化组件
        self.translater: Translater = Translater(self)
        self.timer_manager: TimerManager = TimerManager(self)
        self.keepalive: Keepalive = Keepalive()
        self.hourly_reminder: HourlyReminder = HourlyReminder(self)
        self.monitor_clipboard: MonitorClipboard = MonitorClipboard(self)
        self.clipboard_window: ClipboardWindow = ClipboardWindow(self)

        self.history_manager: HistoryManager = HistoryManager(self.config)
        self.history_window: HistoryWindow = HistoryWindow(self)

        self.log_window: LogWindow = LogWindow(self)
        self.settings_window: SettingsWindow = SettingsWindow(self)
        self.hotkey_listener: HotkeyListener = HotkeyListener(self)
        self.system_tray: SystemTray = SystemTray(self)
        self.todoer: TodoManager = TodoManager(self)
        self.notification_monitor_window = TeamsNotificationsListenerWindow(self)
        logger.info(f"{self.config.app_name} started successfully")
        toolkit_notify(
            title=f"{self.config.app_name} @ {VERSION} started successfully",
            tag="app",
            clear=True,
        )

        globals()["ops_toolkit_app"] = self
        if Path(__file__).parent.parent.joinpath("scripts", "gui_auto.py").exists():
            sys.path.insert(0, str(Path(__file__).parent.parent.joinpath("scripts")))
            # noinspection PyUnresolvedReferences
            from gui_auto import gui_auto
            gui_auto(self)
        self.check_update()
        signal.signal(signal.SIGINT, lambda sig, frame: self.__setattr__("exit_flag", True))
        self.check_flag()

    def check_update(self):
        def check_update(app: "App" = None) -> bool:
            if app is None:
                app = self
            lst_check = Path(self.config.data_dir) / "lst_check_update.txt"
            try:
                if lst_check.exists() and time.time() - int(lst_check.read_text(encoding="utf-8")) < 3600:
                    logger.debug(f"距离上次检查更新不足1小时，跳过检查")
                    return False
                lst_check.write_text(str(int(time.time())))
                return _check_update(app)
            except Exception as e:
                logger.error(f"Check update error: {e}")
                lst_check.unlink(missing_ok=True)

        threading.Thread(target=check_update, args=(self,), daemon=True).start()
        self.root.after(3600_000, self.check_update)

    def check_flag(self):
        if self.exit_flag:
            logger.info(f"Check {self.exit_flag=}")
            self.quit()
        self.root.after(1000, self.check_flag)

    def show_history_window(self):
        """显示历史记录窗口"""
        self.history_window.show()

    def show_log_window(self):
        """显示日志窗口"""
        self.log_window.show()

    def show_settings_window(self):
        """显示设置窗口"""
        self.settings_window.show()

    def show_clipboard_history_window(self):
        """显示剪贴板窗口"""
        self.clipboard_window.show()

    # def show_word_analysis_window(self):
    #     """显示词汇分析窗口"""
    #     self.word_analysis_window.show()

    def run(self):
        """运行应用程序"""
        # 在单独的线程中运行系统托盘
        tray_thread = threading.Thread(target=self.system_tray.run, daemon=True)
        tray_thread.start()

        # 运行主事件循环
        self.root.mainloop()

    def quit(self):
        """退出应用程序"""
        logger.info(f"{self.config.app_name} is exiting")
        self.hotkey_listener.stop()
        self.hourly_reminder.stop()
        self.keepalive.stop()
        self.monitor_clipboard.stop()
        self.root.destroy()
        logger.info(f"{self.config.app_name} is exited.")
        self.exited = True
        sys.exit(0)
