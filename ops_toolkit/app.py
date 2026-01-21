import atexit
import sys
import threading
import tkinter as tk
from logging import getLogger
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

import pyperclip
from PIL import Image
from PIL import ImageTk
from win11toast import notify

from ops_toolkit import VERSION
from ops_toolkit.translate.history import HistoryManager
from ops_toolkit.app_hotkey import HotkeyListener
from ops_toolkit.app_tray import SystemTray
from ops_toolkit.config import config
from ops_toolkit.hourly_reminder.hourly_reminder import HourlyReminder
from ops_toolkit.monitor_clipboard.monitor_clipboard import MonitorClipboard
from ops_toolkit.tools import trans_lang
from ops_toolkit.translate.ui_window_history import HistoryWindow
from ops_toolkit.ui_window_log import LogWindow
from ops_toolkit.ui_window_settings import SettingsWindow
from ops_toolkit.translate.ui_window_translate import TranslationWindow
from ops_toolkit.monitor_clipboard.ui_window_clipboard import ClipboardWindow
from ops_toolkit.monitor_teams.ui_windows_teams_notifications import TeamsNotificationsListenerWindow
from ops_toolkit.keepalive import Keepalive
from ops_toolkit.update_version import check_update

if TYPE_CHECKING:
    from ops_toolkit.config import Config

logger = getLogger("ops_toolkit.app.main")


class App:
    def __init__(self):

        self.version = VERSION
        self.app_name = config.app_name
        self.title = f"{config.app_name} @ {VERSION}"
        # 初始化配置
        logger.info(f"APP Start @ {VERSION} ...")
        self.config: "Config" = config

        # 初始化GUI
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏主窗口

        _img = Image.open(Path(__file__).parent.joinpath("resources/app-icon.png.py").open("rb"))
        self.img = ImageTk.PhotoImage(_img)
        # noinspection PyTypeChecker
        self.root.iconphoto(True, self.img)

        # 初始化组件
        self.keepalive = Keepalive()
        self.hourly_reminder = HourlyReminder(self)
        self.monitor_clipboard = MonitorClipboard(self)
        self.clipboard_window = ClipboardWindow(self)

        self.history_manager = HistoryManager(self.config)
        self.history_window = HistoryWindow(self)

        self.log_window = LogWindow(self)
        self.settings_window = SettingsWindow(self)
        self.hotkey_listener = HotkeyListener(self)
        self.system_tray = SystemTray(self)
        self.notification_monitor_window = TeamsNotificationsListenerWindow(self)
        logger.info(f"{self.config.app_name} started successfully")
        notify(
            app_id=self.config.app_name,
            title=f"{self.config.app_name} @ {VERSION} started successfully"
        )
        globals()["ops_toolkit_app"] = self
        # self.check_new_version()
        check_update(self)
        atexit.register(check_update, self)

    def perform_translation(self):
        """执行翻译操作"""
        try:
            # 读取剪贴板内容
            source_text = pyperclip.paste().strip()

            if not source_text:
                messagebox.showinfo("提示", "剪贴板为空，无法进行翻译")
                return
            src_lang, dst_lang = trans_lang(source_text)
            # 查询该src是否有翻译记录，如果有走历史记录。
            dst_text = self.history_manager.get_record_by_src(source_text).get("dst")
            if dst_text is None:
                logger.info("NOT Found src from history.")
                # 调用翻译API
                translated_text = config.api.translate_text(
                    source_text,
                    to_lang=dst_lang,
                    from_lang=src_lang,
                )
                dst_text = translated_text.dst

                # 记录翻译结果
                self.history_manager.add_record(
                    source_text,
                    dst_text,
                    src_lang,
                    dst_lang
                )
            else:
                logger.info(f"Found src from history. / Use History.")

            # 显示翻译结果
            TranslationWindow(self).show(
                source_text,
                dst_text,
                src_lang,
                dst_lang
            )
        except IndexError:
            logger.info("IndexError: 请先在设置中添加API密钥", exc_info=True)
            messagebox.showinfo("提示", "请先在设置中添加API密钥")
            return

        except Exception as _e:
            logger.error(f"Error during translation: {_e}", exc_info=_e)
            messagebox.showerror("错误", f"翻译过程中发生错误:\n{str(_e)}")

    # def check_new_version(self):
    #     """检查是否有新版本"""
    #     try:
    #         from ops_toolkit.update_version import check_update
    #         threading.Thread(target=check_update, args=(self,)).start()
    #     finally:
    #         self.root.after(60 * 60 * 1000, self.check_new_version, )

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
        self.root.destroy()
        logger.info(f"{self.config.app_name} is exited.")
        sys.exit(0)


def quit_app():
    """退出应用程序"""
    if globals().get("ops_toolkit_app", None) is not None:
        globals().get("ops_toolkit_app").quit()


def get_app() -> App:
    """获取应用程序实例"""
    if globals().get("ops_toolkit_app", None) is None:
        raise ValueError("App instance not found. Please run the app first.")
    return globals().get("ops_toolkit_app")

# # 主程序入口
# if __name__ == "__main__":
#     try:
#         app = App()
#         app.run()
#     except Exception as e:
#         logger.critical(f"Application crashed: {e}", exc_info=True)
#         sys.exit(1)
