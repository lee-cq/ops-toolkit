#!/usr/bin/env python
# -*- coding: utf-8 -*-
import concurrent.futures
import logging
import queue
import re
import tempfile
import typing
from pathlib import Path
from threading import Timer
from typing import Callable
from typing import Union

import PIL.BmpImagePlugin
import PIL.ImageGrab
import pyperclip
import win11toast

from ops_toolkit.zhconv import convert
from ops_toolkit.config import config

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.tools")


def get_clipboard_content() -> tuple[str, Union[str, list[str], PIL.BmpImagePlugin.BmpImageFile, None]]:
    """
    获取剪切板数据，返回内容类型和数据

    Returns:
      Tuple[str, Union[str, bytes, List[str], None]]:
          - 第一个元素是内容类型: "text", "image", "files", "empty", "error"
          - 第二个元素是实际数据:
              * 文本内容 (str) 当类型为 "text"
              * 图像数据 (bytes) 当类型为 "image"
              * 文件路径列表 (List[str]) 当类型为 "files"
              * None 当类型为 "empty" 或 "error"
    """
    try:
        text = pyperclip.paste()
        if text:
            return "text", text

        image = PIL.ImageGrab.grabclipboard()
        if isinstance(image, PIL.BmpImagePlugin.BmpImageFile):
            return "image", image

        if isinstance(image, list):
            return "files", image

        return "empty", None
    except Exception as e:
        return "error", f"剪切板内容获取失败: {str(e)}"


def auto_lang(text: str) -> str:
    """自动识别语言

    :param text:
    :return:
    """
    # 定义各语言字符范围的正则模式（扩展繁体中文匹配范围，包含常见繁体字符）
    no_ascii_pattern = re.compile(r'[\u4e00-\u9fa5\u3400-\u4db5\u7e00-\u9fef\uf900-\ufa2d]')

    en_map = {
        ".":  " ",
        "'":  "",
        "\"": "",
        ",":  " ",
        "?":  " ",
        "!":  " ",
        ":":  " ",
        ";":  " ",
    }

    text = convert(text, "zh-cn")

    en_text = "".join((_ for _ in text if ord(_) < 128)).translate(str.maketrans(en_map))
    en_count = len([word for word in en_text.split() if word])
    zh_count = len([1 for _ in text if no_ascii_pattern.match(_)])

    # 根据字符计数判断主要语言
    if en_count > zh_count:
        return 'en'
    else:
        return 'zh'


def trans_lang(text: str) -> tuple[str, str]:
    """根据输入文本自动识别语言并返回源语言和目标语言

    简体中文 -> ["zh", "en"]
    繁体中文 -> ["tw", "zh"]
    英文 -> ["en", "zh"]

    :param text:
    :return:
    """
    src_lang = auto_lang(text)

    # 根据源语言返回对应结果
    if src_lang == 'zh':
        return "zh", "en"
    elif src_lang == 'tw':
        return "tw", "zh"
    elif src_lang == 'en':
        return "en", "zh"
    else:
        # 处理未预期的语言识别结果，默认返回英文到中文
        return "en", "zh"


class StartLock:
    def __init__(self, ):
        self.lock_file = Path(tempfile.gettempdir()).joinpath("py_ops_toolkit_app.lock")
        import msvcrt
        import sys
        import atexit
        import logging

        self.logger = logging.getLogger("ops_toolkit.lock")
        try:
            self.fd = self.lock_file.open('w')
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
            self.logger.info(f"Get lock file. fileno: {self.fd.fileno()}")
            atexit.register(self.release)
        except (BlockingIOError, PermissionError):
            self.logger.error("Another instance of the ops-toolkit is already running.")
            from tkinter import messagebox
            messagebox.showerror(
                "ops-toolkit Start Error",
                "另一个进程已在运行中 ...\n"
                "1. 检查托盘图标是否被隐藏\n"
                "2. 通过任务管理器结束该进程")
            sys.exit(1)

    def release(self):

        if self.fd is not None and not self.fd.closed:
            self.fd.close()
            self.logger.info("Lock file closed.")
        if self.lock_file.exists():
            self.lock_file.unlink()
            self.logger.info("Lock file released.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class GUIHandler(logging.Handler):
    def __init__(self, queue_: queue.Queue):
        super().__init__()
        self.queue_ = queue_
        self.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s"))

    def emit(self, record: logging.LogRecord):
        if self.queue_.full():
            self.queue_.get()
        self.queue_.put(self.format(record))


def toolkit_notify(title: str, message: str = "", tag: str = None, clear: bool = False, **kwargs):
    """
    使用Windows系统通知进行通知
    """
    group = config.app_name
    kwargs["group"] = group
    if clear and tag:
        logger.info(f"Clear toast: {group=}")
        # clear_toast(app_id=config.app_name, group=group, tag=tag) ToDo Win11toast更新
    win11toast.notify(title, message, app_id=config.app_name, tag=tag, **kwargs)


def toolkit_notify_callback(
        title: str,
        message: str = "",
        tag: str = None,
        clear: bool = False,
        callbacks: dict[str, Callable[[], None]] = None,
        timeout: int = 30,
        timeout_callback: Callable[[], None] = None,
        **kwargs):
    """
    使用Windows系统通知进行通知
    """
    group = config.app_name
    kwargs["group"] = group
    if clear and tag:
        logger.info(f"Clear toast: {group=}")
        # clear_toast(app_id=config.app_name, group=group, tag=tag) ToDo Win11toast更新

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                win11toast.toast,
                title,
                message,
                app_id=config.app_name,
                buttons=callbacks.keys(),
                tag=tag,
                **kwargs
            )
            result = future.result(timeout=timeout)
            logger.debug(f"Notify Result: {result}")
            if callbacks:
                callbacks.get(result["arguments"].replace("http:", ""), timeout_callback)()
    except (concurrent.futures.TimeoutError or KeyError or TypeError) as _e:
        logger.info(f"Timeout Or KeyError, {_e}")
        if callable(timeout_callback):
            timeout_callback()


class DaemonTimer(Timer):
    def __init__(self, interval, function, args=None, kwargs=None):
        super().__init__(interval, function, args, kwargs)
        self.daemon = True


class TimerManager:
    def __init__(self, app: "App"):
        self.app = app
        self.timers: dict[str, Timer] = dict()

    def new(self, interval, function, args=None, kwargs=None) -> Timer:
        _t = Timer(interval, function, args, kwargs)
        _t.name = f"{function.__name__}({args}, {kwargs})"
        _t.daemon = True
        self.timers[_t.name] = _t
        return _t

    def cancel(self, timer: Timer):
        timer.cancel()
        self.timers.pop(timer.name)

    def cancel_all(self):
        for timer in self.timers.values():
            self.cancel(timer)
