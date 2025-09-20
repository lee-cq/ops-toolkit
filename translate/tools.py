#!/usr/bin/env python
# -*- coding: utf-8 -*-


# !/usr/bin/env python
# -*- coding: utf-8 -*-

import re


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


def trans_lang(text: str) -> [str, str]:
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
        return ["zh", "en"]
    elif src_lang == 'tw':
        return ["tw", "zh"]
    elif src_lang == 'en':
        return ["en", "zh"]
    else:
        # 处理未预期的语言识别结果，默认返回英文到中文
        return ["en", "zh"]
