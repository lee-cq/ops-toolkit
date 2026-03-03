#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2025/9/20 17:35

app 入口， 接收一个参数 config指定配置文件的位置， 默认为 config.toml
"""

import argparse
import logging
import os
import warnings

from ops_toolkit.log import init_logger
from ops_toolkit.tools import StartLock
from ops_toolkit.config import config

logger = logging.getLogger("ops_toolkit.app.main")

warnings.filterwarnings("ignore", category=SyntaxWarning)


def _main():
    """主函数入口"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='翻译工具')
    parser.add_argument(
        '--config',
        default='',
        help='指定配置文件路径，默认为 ~/.config/ops_toolkit/config.toml'
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置环境变量
    if args.config:
        os.environ["OPS_TOOLKIT_CONFIG_PATH"] = args.config
        # BUG 设置环境变量是不生效，因为config在该关键变量被指定前就完成了导入

    logger.info("starting ...")
    # 导入应用类
    from ops_toolkit.app import App

    # 创建并运行应用
    app = App()
    app.run()


def main():
    try:
        init_logger()
        with StartLock():
            _main()
    except KeyboardInterrupt:
        from win11toast import notify
        notify(
            app_id=config.app_name,
            title=f"{config.app_name} APP Exited."
        )
    except Exception as e:
        from tkinter import messagebox
        logger.error(f"{config.app_name} Start Error: {e}", exc_info=True)
        messagebox.showerror(f"{config.app_name} Start Error", f"{e}")


if __name__ == '__main__':
    main()
