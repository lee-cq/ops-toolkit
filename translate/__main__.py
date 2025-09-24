#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2025/9/20 17:35

app 入口， 接收一个参数 config指定配置文件的位置， 默认为 config.toml
"""

import argparse
import os


def main():
    """主函数入口"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='翻译工具')
    parser.add_argument(
        '--config',
        default='',
        help='指定配置文件路径，默认为 ~/.config/translate/config.toml'
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置环境变量
    if args.config:
        os.environ["TRANSLATE_CONFIG_PATH"] = args.config

    # 导入应用类
    from translate.app import TranslationApp

    # 创建并运行应用
    app = TranslationApp()
    app.run()


if __name__ == '__main__':
    main()
