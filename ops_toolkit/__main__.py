#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2025/9/20 17:35

ops-toolkit 统一入口
- ops-toolkit             → 后台启动主程序（GUI 模式）
- ops-toolkit gui         → 显式 GUI 模式 → 后台启动主程序
- ops-toolkit-cli         → CLI 模式 → 前台启动主程序，实时输出日志
- ops-toolkit-cli <cmd>   → 执行子命令 → 先检查主程序是否运行，未运行则提示并 exit(1)
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
    """启动主程序 App"""
    logger.info("starting ...")
    from ops_toolkit.app import App
    app = App()
    app.run()


def _start_app_background():
    """在后台进程中启动主程序"""
    import subprocess
    import sys

    # 使用 pythonw.exe 在后台启动（无控制台窗口）
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable

    env = os.environ.copy()
    # 传递配置文件路径
    config_path = os.environ.get("OPS_TOOLKIT_CONFIG_PATH", "")

    # 在新进程中启动主程序
    try:
        subprocess.Popen(
            [pyw, "-m", "ops_toolkit"],
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            close_fds=True,
        )
        typer.echo("ops-toolkit 已在后台启动。")
    except FileNotFoundError:
        # 回退到当前 python
        subprocess.Popen(
            [sys.executable, "-m", "ops_toolkit"],
            env=env,
            start_new_session=True,
        )
        typer.echo("ops-toolkit 已在后台启动。")


# ============ ops-toolkit 子命令（主程序入口） ============

@tp.command("gui", help="后台启动主程序（GUI 模式）", hidden=True)
def cmd_gui():
    """后台启动主程序"""
    from ops_toolkit.log import init_logger
    init_logger()
    _start_app()


@tp.command("cli", hidden=True)
def cmd_cli():
    """前台启动主程序（CLI 模式，实时日志）"""
    from ops_toolkit.log import init_logger
    init_logger()
    _start_app()


def _default_command(config: Optional[str] = None):
    """默认命令（不带参数时执行）"""
    from ops_toolkit.log import init_logger
    from ops_toolkit.tools import StartLock

    if config:
        os.environ["OPS_TOOLKIT_CONFIG_PATH"] = config

    try:
        init_logger()
        with StartLock():
            _start_app()
    except KeyboardInterrupt:
        logger.info("Exited by user.")
    except Exception as e:
        from ops_toolkit.config import config as cfg
        logger.error(f"{cfg.app_name} Start Error: {e}", exc_info=True)


@tp.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Annotated[Optional[str], typer.Argument(help="指定配置文件路径")] = None,
    version: Annotated[bool, typer.Option("--version", "-v", help="显示版本信息")] = False,
):
    if version:
        from ops_toolkit import VERSION
        print(f"{VERSION}")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    # 没有子命令 → 默认启动主程序（GUI 模式）
    _default_command(config)


# ============ ops-toolkit-cli 入口 ============

cli_tp = typer.Typer(
    name="ops-toolkit-cli",
    help="ops-toolkit CLI — 命令行管理工具",
    no_args_is_help=False,
    add_completion=False,
)


def _require_server_running():
    """检查主程序是否运行，未运行则提示并退出"""
    from ops_toolkit.cli.client import CLIClient
    if not CLIClient().check_health():
        typer.echo("Error: 主程序未运行，请先启动 ops-toolkit。", err=True)
        raise typer.Exit(1)


@cli_tp.callback(invoke_without_command=True)
def cli_main(
    ctx: typer.Context,
    foreground: Annotated[bool, typer.Option("--foreground", "-f", help="前台启动模式（实时日志）")] = False,
):
    """ops-toolkit CLI 管理工具

    不带子命令时，前台启动主程序并输出实时日志。
    使用子命令时，先检查主程序是否运行。
    """
    if ctx.invoked_subcommand is not None:
        # 有子命令 → 先检查主程序是否运行
        _require_server_running()
        return

    # 没有子命令 → 前台启动主程序
    from ops_toolkit.log import init_logger
    from ops_toolkit.tools import StartLock

    try:
        init_logger()
        with StartLock():
            _start_app()
    except KeyboardInterrupt:
        logger.info("Exited by user.")
    except Exception as e:
        from ops_toolkit.config import config as cfg
        logger.error(f"{cfg.app_name} Start Error: {e}", exc_info=True)


# 注册 CLI 子命令
from ops_toolkit.cli.cmds_app import app_cmd
from ops_toolkit.cli.cmds_config import config_cmd
from ops_toolkit.cli.cmds_todo import todo_cmd
from ops_toolkit.cli.cmds_component import component_cmd
from ops_toolkit.cli.cmds_translate import translate_cmd

cli_tp.add_typer(app_cmd, name="app")
cli_tp.add_typer(config_cmd, name="config")
cli_tp.add_typer(todo_cmd, name="todo")
cli_tp.add_typer(component_cmd, name="component")
cli_tp.add_typer(translate_cmd, name="translate")


# ============ 独立入口函数 ============

def cli_entry():
    """ops-toolkit-cli 入口函数"""
    cli_tp()


if __name__ == '__main__':
    tp()
