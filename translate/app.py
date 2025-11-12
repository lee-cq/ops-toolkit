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

from translate import VERSION
from translate.app_history import HistoryManager
from translate.app_hotkey import HotkeyListener
from translate.app_tray import SystemTray
from translate.config import config
from translate.other_tools.hourly_reminder import HourlyReminder
from translate.tools import trans_lang
from translate.ui_window_history import HistoryWindow
from translate.ui_window_log import LogWindow
from translate.ui_window_settings import SettingsWindow
from translate.ui_window_translate import TranslationWindow
from translate.other_tools.keepalive import Keepalive

if TYPE_CHECKING:
    from translate.config import Config

logger = getLogger("translate.app.main")


class TranslationApp:
    def __init__(self):

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
        self.history_manager = HistoryManager(self.config)
        # self.translation_window = TranslationWindow(self)
        self.history_window = HistoryWindow(self)
        self.log_window = LogWindow(self)
        self.settings_window = SettingsWindow(self)
        self.hotkey_listener = HotkeyListener(self)
        self.system_tray = SystemTray(self)
        self.export_to_feishu_every_hour()
        logger.info(f"{self.config.app_name} started successfully")
        notify(f"{self.config.app_name} @ {VERSION} started successfully")

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

        except Exception as _e:
            logger.error(f"Error during translation: {_e}", exc_info=_e)
            messagebox.showerror("错误", f"翻译过程中发生错误:\n{str(_e)}")

    def show_history_window(self):
        """显示历史记录窗口"""
        self.history_window.show()

    def show_log_window(self):
        """显示日志窗口"""
        self.log_window.show()

    def show_settings_window(self):
        """显示设置窗口"""
        self.settings_window.show()

    # def show_word_analysis_window(self):
    #     """显示词汇分析窗口"""
    #     self.word_analysis_window.show()

    # noinspection PyTypeChecker
    def export_to_feishu_every_hour(self):
        """导出历史记录到飞书"""
        try:
            msg = self.history_manager.export_feishu()
            if msg != "没有新的记录":
                messagebox.showinfo("导出到飞书成功", msg)
        except Exception as _e:
            logger.error(f"Error during export: {_e}", exc_info=_e)
            msg = f"Error during export: {_e}"
            messagebox.showerror("导出到飞书失败", msg)

        finally:
            self.root.after(60 * 60 * 1000, self.export_to_feishu_every_hour)

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


# 主程序入口
if __name__ == "__main__":
    try:
        app = TranslationApp()
        app.run()
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)
