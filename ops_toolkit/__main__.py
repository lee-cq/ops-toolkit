#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2025/9/20 17:35

ops-toolkit 统一入口

ops-toolkit (pythonw.exe) 和 ops-toolkit-cli (python.exe) 共用此入口。
唯一的区别：pythonw.exe 启动时 sys.stdout 为 None（无控制台窗口），
python.exe 启动时 sys.stdout 有效（有控制台窗口，日志实时可见）。
"""

import logging
import os
import sys
import warnings
from typing import Annotated, Optional

import typer

logger = logging.getLogger("ops_toolkit.app.main")

warnings.filterwarnings("ignore", category=SyntaxWarning)

tp = typer.Typer(
    name="ops-toolkit",
    help="ops-toolkit — 运维工具包",
    no_args_is_help=False,
    add_completion=False,
)


def _start_app():
    """启动主程序"""
    logger.info("starting ...")
    from ops_toolkit.app import App

    app = App()
    app.run()


@tp.callback(invoke_without_command=True)
def main(
        ctx: typer.Context,
        config: Annotated[Optional[str], typer.Argument(help="指定配置文件路径")] = None,
        version: Annotated[bool, typer.Option("--version", "-v", help="显示版本信息")] = False
):
    """ops-toolkit 统一入口

    不带子命令时启动主程序。带子命令时执行 CLI 管理命令。
    """
    if version:
        from ops_toolkit import VERSION

        print(f"{VERSION}")
        raise typer.Exit()

    # 有子命令 → 先检查主程序是否运行
    if ctx.invoked_subcommand is not None:
        from ops_toolkit.cli.client import CLIClient

        if not CLIClient().check_health():
            typer.echo("Error: 主程序未运行，请先启动 ops-toolkit。", err=True)
            raise typer.Exit(1)
        return

    # 没有子命令 → 启动主程序
    if config:
        os.environ["OPS_TOOLKIT_CONFIG_PATH"] = config

    from ops_toolkit.log import init_logger
    from ops_toolkit.tools import StartLock
    from ops_toolkit.tools import toolkit_notify

    try:
        init_logger()
        with StartLock():
            _start_app()
    except KeyboardInterrupt:
        from ops_toolkit.config import config as cfg

        logger.info("Exited by user.")
        toolkit_notify(
            title=f"{cfg.app_name} APP Exited.",
            tag="app",
            clear=True
        )
    except Exception as e:
        from ops_toolkit.config import config as cfg

        from tkinter import messagebox
        logger.error(f"{cfg.app_name} Start Error: {e}", exc_info=True)
        messagebox.showerror(f"{cfg.app_name} Start Error", f"{e}")


# 注册 CLI 子命令到同一个 Typer App
from ops_toolkit.cli.cmds_app import app_cmd
from ops_toolkit.cli.cmds_config import config_cmd
from ops_toolkit.cli.cmds_todo import todo_cmd
from ops_toolkit.cli.cmds_component import component_cmd
from ops_toolkit.cli.cmds_translate import translate_cmd

tp.add_typer(app_cmd, name="app")
tp.add_typer(config_cmd, name="config")
tp.add_typer(todo_cmd, name="todo")
tp.add_typer(component_cmd, name="component")
tp.add_typer(translate_cmd, name="translate")

if __name__ == '__main__':
    tp()
