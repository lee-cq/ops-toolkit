#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2025/9/20 17:35

app 入口， 接收一个参数 config指定配置文件的位置， 默认为 config.toml
"""

import logging
import os
import warnings
from typing import Annotated
from typing import Optional

import typer

logger = logging.getLogger("ops_toolkit.app.main")

warnings.filterwarnings("ignore", category=SyntaxWarning)

tp = typer.Typer()


def _main():
    """主函数入口"""

    logger.info("starting ...")
    # 导入应用类

    from ops_toolkit.app import App

    # 创建并运行应用
    app = App()
    app.run()


@tp.command()
def main(
        config: Annotated[Optional[str], typer.Argument()] = None,
        version: Annotated[bool, typer.Option("--version", "-v", help="显示版本信息")] = False
):
    if version:
        from ops_toolkit import VERSION
        print(f"{VERSION}")
        return

    from ops_toolkit.log import init_logger
    from ops_toolkit.tools import StartLock
    from ops_toolkit.tools import toolkit_notify

    if config:
        os.environ["OPS_TOOLKIT_CONFIG_PATH"] = config

    try:
        init_logger()
        with StartLock():
            _main()
    except KeyboardInterrupt:
        from ops_toolkit.config import config

        logger.info("Exited by user.")
        toolkit_notify(
            title=f"{config.app_name} APP Exited.",
            tag="app",
            clear=True
        )
    except Exception as e:
        from ops_toolkit.config import config

        from tkinter import messagebox
        logger.error(f"{config.app_name} Start Error: {e}", exc_info=True)
        messagebox.showerror(f"{config.app_name} Start Error", f"{e}")


if __name__ == '__main__':
    tp()
