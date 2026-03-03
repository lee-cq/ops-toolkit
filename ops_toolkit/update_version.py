#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : update_version.py
@Author     : LeeCQ
@Date-Time  : 2026/1/21 07:15
"""
import logging
import os
import re
import subprocess
import sys
import typing
from pathlib import Path

import requests
from ops_toolkit import VERSION
from ops_toolkit.config import config

if typing.TYPE_CHECKING:
    from ops_toolkit.app import App

logger = logging.getLogger("ops_toolkit.update")

SCRIPT = """
@echo off
set pid={pid}

echo Try to close the process after waiting for 5 seconds ...
timeout /T 5 && taskkill /F /PID %pid%

echo update ops-toolkit {old_version} -> {new_version}

where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo Use uv to update ops-toolkit to {new_version}
    uv tool update ops-toolkit=={new_version} -i {registry}
) else (
    echo Use pip to update ops-toolkit to {new_version}
    {py_exe} -m pip install --upgrade ops-toolkit=={new_version} -i {registry}
)
echo Update ops-toolkit to {new_version} done.
pause
 
start "" "{pyw_exe}" -m ops_toolkit
exit /b 0
"""

DEFAULT_VERSION = (0, 0, 0, 99)


class UpdateVersion:
    """更新版本"""

    def __init__(self, app: "App" = None):
        self.app = app
        logger.info("checking new version ...")
        self.update_script = Path(config.data_dir).joinpath("update_version.bat")
        self.skip_version_file = config.data_dir.joinpath("SKIP_VERSION")
        self.old_version = self.get_local_version()
        self.old_version_str = self.version_to_str(self.old_version)
        self.new_version = self.get_remote_version()
        self.new_version_str = self.version_to_str(self.new_version)

        logger.info(f"当前版本: {self.old_version_str=} 远程版本: {self.new_version_str=}")

    @staticmethod
    def version_to_tuple(version: str) -> tuple[int, int, int, int]:
        beta = int(version.split("b")[1]) if 'b' in version else 99
        _m = list(map(int, version.split("b")[0].split(".")))
        return _m[0], _m[1], _m[2], beta

    @staticmethod
    def version_to_str(version: tuple[int, ...]) -> str:
        if len(version) == 3:
            return ".".join(map(str, version))
        else:
            return ".".join(map(str, version[:3])) + (f"b{version[3]}" if version[3] != 99 else "")

    def get_remote_version(self) -> tuple[int, ...]:
        """获取远程版本号

        :return:
        """
        try:
            response = requests.get("https://cnb.cool/leecq/pytools/-/registries/ops-toolkit/-/tags")
            response.raise_for_status()
            versions = re.findall(r"/leecq/pytools/-/registries/ops-toolkit/-/tag/(\d\.\d+\.\d+[b\d]*)", response.text)
            logger.info(f"在制品库中找到版本号: {versions}")
            acc_beta = config.startup_beta
            return max(self.version_to_tuple(i) for i in versions if ("b" in i and acc_beta) or "b" not in i)
        except requests.RequestException as e:
            logger.error(f"获取远程版本号失败: {e}")
            return DEFAULT_VERSION

    def get_local_version(self) -> tuple[int, ...]:
        """获取本地版本号

        :return:
        """
        if self.skip_version_file.exists():
            _skip_version = self.version_to_tuple(self.skip_version_file.read_text().strip())
            logger.debug(f"跳过版本文件: {self.skip_version_file} {_skip_version}")
        else:
            _skip_version = DEFAULT_VERSION
        return max(self.version_to_tuple(VERSION), _skip_version)

    def write_update_script(self):
        """写入更新脚本"""
        _sp = SCRIPT.format(
            pyw_exe=Path(sys.executable).with_name("pythonw.exe"),
            py_exe=sys.executable,
            pid=os.getpid(),
            new_version=self.new_version_str,
            old_version=self.old_version_str,
            registry=config.registry,
        )
        logger.info(f"更新脚本: {_sp}\n========================")
        with open(self.update_script, "w", encoding="utf-8") as f:
            f.write(_sp)

    def check(self) -> bool:
        """检查是否有更新

        :return:
        """
        if self.new_version <= self.old_version:
            logger.debug(f"当前版本 {self.old_version_str} 大于等于远程版本 {self.new_version_str}, 或已跳过该版本")
            return False

        logger.info(f"发现新版本: {self.old_version_str} -> {self.new_version_str}")
        self.show()
        return True

    def show(self):
        """弹窗提示用户是否需要升级：
        1. 升级
        2. 跳过
        3. 取消
        """
        from tkinter import messagebox

        ret = messagebox.askyesnocancel(
            "更新提示",
            f"发现新版本: {self.old_version_str} -> {self.new_version_str}\n是否升级？\n\n"
            "是：升级到最新版本\n"
            f"否：跳过该版本: {self.new_version_str}\n"
            "取消：取消本次升级"
        )

        if ret:
            logger.info("用户选择升级")
            self.write_update_script()
            logger.info(f"已生成更新脚本: {self.update_script}")
            subprocess.run(["cmd", "/c", "start", "", str(self.update_script)], check=True)
            if self.app is not None:
                self.app.quit()
        elif ret is False:
            logger.info(f"用户选择跳过升级: {self.new_version_str}")
            self.skip_version_file.write_text(self.new_version_str)
        else:
            logger.info("用户取消升级")


def check_update(app: "App" = None) -> bool:
    """检查更新"""
    return UpdateVersion(app).check()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # VERSION = "1.0.0"
    UpdateVersion().check()
