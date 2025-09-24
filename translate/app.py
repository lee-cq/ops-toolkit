import logging.config
import sys
import threading
import tkinter as tk
from logging import getLogger
from pathlib import Path

from PIL import Image, ImageTk

from translate.config import config
from translate.app_history import HistoryManager
from translate.tools import trans_lang
from translate.ui_window_translate import TranslationWindow
from translate.ui_window_history import HistoryWindow
from translate.ui_window_log import LogWindow
from translate.ui_window_settings import SettingsWindow
from translate.ui_window_analysis import WordAnalysisWindow
from translate.app_hotkey import HotkeyListener
from translate.app_tray import SystemTray
from translate.app_analyzer import TextAnalyzer

logger = getLogger("translate.app.main")


def init_logger():
    """初始化日志配置"""
    logging.config.dictConfig(
        {
            'version': 1,
            # 'disable_existing_loggers': False,
            'formatters': {
                'translate_formatter': {
                    'format': '%(asctime)s - %(filename)s - [%(levelname)s] - %(message)s',  # 包含时间、logname、等级、msg
                    'datefmt': '%Y-%m-%d %H:%M:%S'  # 时间格式
                }
            },
            'handlers': {
                'console_handler': {
                    'class': 'logging.StreamHandler',  # 控制台输出
                    'formatter': 'translate_formatter',
                    'level': 'DEBUG'  # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
                },
                'file_handler': {
                    'class': 'logging.FileHandler',  # 文件输出
                    'filename': config.log_path,  # 日志文件名
                    'formatter': 'translate_formatter',
                    'level': 'INFO',  # 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
                    "encoding": "utf-8"
                }
            },
            "filters": {},
            'loggers': {
                'translate': {  # 指定translate日志器
                    'handlers': ['console_handler', 'file_handler'],
                    'level': 'DEBUG',
                    'propagate': False  # 不向上传播日志
                }
            }
        }
    )


class TranslationApp:
    def __init__(self):
        init_logger()
        # 初始化配置
        self.config = config

        # 初始化GUI
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏主窗口

        _img= Image.open(Path(__file__).parent.joinpath("resources/app-icon.png.py").open("rb"))
        self.img = ImageTk.PhotoImage(_img)
        self.root.iconphoto(True, self.img)

        # 初始化组件
        self.history_manager = HistoryManager(self.config)
        self.analyzer = TextAnalyzer(self.history_manager)
        # self.translation_window = TranslationWindow(self)
        self.history_window = HistoryWindow(self)
        self.log_window = LogWindow(self)
        self.settings_window = SettingsWindow(self)
        self.word_analysis_window = WordAnalysisWindow(self)
        self.hotkey_listener = HotkeyListener(self)
        self.system_tray = SystemTray(self)

        logger.info(f"{self.config.app_name} started successfully")

    def perform_translation(self):
        """执行翻译操作"""
        try:
            # 读取剪贴板内容
            import pyperclip
            source_text = pyperclip.paste().strip()

            if not source_text:
                tk.messagebox.showinfo("提示", "剪贴板为空，无法进行翻译")
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
            tk.messagebox.showerror("错误", f"翻译过程中发生错误:\n{str(_e)}")

    def show_history_window(self):
        """显示历史记录窗口"""
        self.history_window.show()

    def show_log_window(self):
        """显示日志窗口"""
        self.log_window.show()

    def show_settings_window(self):
        """显示设置窗口"""
        self.settings_window.show()

    def show_word_analysis_window(self):
        """显示词汇分析窗口"""
        self.word_analysis_window.show()

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
        sys.exit(0)


# 主程序入口
if __name__ == "__main__":
    try:
        app = TranslationApp()
        app.run()
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)
