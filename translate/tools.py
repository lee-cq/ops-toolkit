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
    # 定义各语言字符范围的正则模式
    traditional_pattern = re.compile(r'[\u3400-\u4db5\u9fa6-\u9fef\uf900-\ufa2d]')
    simplified_pattern = re.compile(r'[\u4e00-\u9fa5]')

    en_count = 0
    zh_cn_count = 0
    zh_tw_count = 0

    for c in text:
        if traditional_pattern.match(c):
            zh_tw_count += 1
        elif simplified_pattern.match(c):
            zh_cn_count += 1
        elif c.isalpha():
            en_count += 1

    # 根据字符计数判断主要语言
    if en_count > zh_cn_count and en_count > zh_tw_count:
        return 'en'
    elif zh_tw_count > zh_cn_count:
        return 'zh-TW'
    else:
        return 'zh-CN'