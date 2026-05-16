#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : main.py
@Author     : LeeCQ
@Date-Time  : 2026/3/10 04:49
"""
import logging
import typing
import re

import pyperclip
from tkinter import messagebox

from ops_toolkit.config import config
from ops_toolkit.tools import trans_lang
from ops_toolkit.translate.ui_window_translate import TranslationWindow

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.translate")

__all__ = ["Translater"]


class Translater:
    """翻译器"""

    def __init__(self, app: "App"):
        self.app = app

    @staticmethod
    def src_text_cat(st: str) -> str:
        """"""
        # 移除连续的换行
        st = "\n".join(i for i in st.strip().split("\n") if i.strip() != "")
        # 处理驼峰
        for i in re.finditer(r'[a-z][A-Z][a-z]', st):
            _old = i.group(0)
            st = st.replace(_old, "".join((_old[0], " ", _old[1], _old[2])))
        # 处理下划线
        st = st.replace("_", " ")
        return st

    def perform_translation(self):
        """执行翻译操作"""
        try:
            # 读取剪贴板内容
            source_text = pyperclip.paste().strip()

            if not source_text:
                messagebox.showinfo("提示", "剪贴板为空，无法进行翻译")
                return
            source_text = self.src_text_cat(source_text)
            src_lang, dst_lang = trans_lang(source_text)
            # 查询该src是否有翻译记录，如果有走历史记录。
            dst_text = self.app.history_manager.get_record_by_src(source_text).get("dst")
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
                self.app.history_manager.add_record(
                    source_text,
                    dst_text,
                    src_lang,
                    dst_lang
                )
            else:
                logger.info(f"Found src from history. / Use History.")

            # 显示翻译结果
            self.app.root.after(10, TranslationWindow(self.app).show,
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
