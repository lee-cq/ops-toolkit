#!/usr/bin/env python
# -*- coding: utf-8 -*-


# !/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import tempfile
from pathlib import Path


def auto_lang(text: str) -> str:
    """自动识别语言

    :param text:
    :return:
    """
    # 定义各语言字符范围的正则模式（扩展繁体中文匹配范围，包含常见繁体字符）
    traditional_pattern = re.compile(r'[\u3400-\u4db5\u7e00-\u9fef\uf900-\ufa2d]')
    simplified_pattern = re.compile(r'[\u4e00-\u9fa5]')

    en_count = 0
    zh_cn_count = 0
    zh_tw_count = 0

    for c in text:
        if traditional_pattern.match(c):
            zh_tw_count += 1
        elif simplified_pattern.match(c):
            zh_cn_count += 1
        elif ord(c) < 128:
            en_count += 1

    # 根据字符计数判断主要语言
    if en_count > zh_cn_count + zh_tw_count:
        return 'en'
    elif zh_tw_count >= zh_cn_count:
        return 'tw'
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
        self.lock_file = Path(tempfile.gettempdir()).joinpath("py_translate_app.lock")
        import msvcrt
        import sys
        import atexit
        import logging

        self.logger = logging.getLogger("translate.lock")
        try:
            self.fd = self.lock_file.open('w')
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
            self.logger.info(f"Get lock file. fileno: {self.fd.fileno()}")
            atexit.register(self.release)
        except (BlockingIOError, PermissionError):
            self.logger.error("Another instance of the Translator is already running.")
            from tkinter import messagebox
            messagebox.showerror("Translator Start Error", "另一个进程已在运行中。")
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
