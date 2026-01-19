#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : aliyun_sls_split.py
@Author     : LeeCQ
@Date-Time  : 2025/12/28 04:41

Aliyun SLS 日志文件切割工具。

输入：
    一个gzip压缩的文本的文件，一行一个json结果；
    json中包含如下key:
        __source__  日志来源IP
        __tag__:__hostname__ 日志来源主机名
        __tag__:__path__  日志来源文件名
        __time__  日志时间
        content   日志内容

1. 是否需要按照__path__ 分割到不同文件 - 默认： True
2. 是否需要按照__hostname__分割到不同文件 - 默认: False
3. 是否需要移除__path__中的数字 - 默认: False

"""
import datetime
import logging
import json
import gzip
import os
import queue
import re
from pathlib import Path

import requests

logger = logging.getLogger("")

re_all_num = re.compile(r"\d+")


def strip_path_num(path: str):
    """移除路径中的数字"""

    def _sep(s, p):
        return p.join((_ for _ in s.split(p) if not re_all_num.match(_)))

    for sep in "-_=":
        path = _sep(path, sep)
    return path


class LogSplit:

    def __init__(
            self,
            uri: str,
            workdir="",
            diff_path=True,
            diff_hostname=False,
            remove_path_num=False,
            single_file=False,
    ):
        self.uri = uri
        self.source_name = Path(uri).stem
        self.js_data = None
        self.diff_path = diff_path
        self.diff_hostname = diff_hostname
        self.remove_path_num = remove_path_num
        self.single_file = single_file

        self.min_time = -1
        self.max_time = -1
        self.total_line = 0
        self.status = None
        self.gui_logs = queue.Queue()
        self.workdir = (
            Path(workdir)
            if workdir else
            Path(os.environ.get("USERPROFILE")).joinpath("Downloads", "log_down")
        ).joinpath(self.source_name.split(".")[0])
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.log_files = dict()

    def __repr__(self):
        return f"LogSplit({self.source_name} <{self.min_time}, {self.max_time}>"

    def setup_time(self, date: int):
        _t = int(date)
        if self.min_time == -1:
            self.min_time = _t
        if self.max_time == -1:
            self.max_time = _t

        if _t < self.min_time:
            self.min_time = _t
        if _t > self.max_time:
            self.max_time = _t

    def get_data(self, uri: str):
        self.status = "download"
        self.gui_logs.put(f"开始下载日志文件: {self.source_name}")

        if uri.startswith("http"):
            resp = requests.get(uri)
            self.js_data = gzip.decompress(resp.content)
            self.workdir.joinpath(self.source_name).write_bytes(self.js_data)

        else:
            self.js_data = gzip.decompress(open(uri, "rb").read())

    def logs_close(self):
        for f in self.log_files.values():
            try:
                f.close()
            finally:
                pass

    def join_file_name(self, name, hostname, ip=""):
        filename_l = []
        if self.diff_path:
            if self.remove_path_num:
                filename_l.append(strip_path_num(Path(name).stem))
            else:
                filename_l.append(Path(name).stem)

        if self.diff_hostname:
            filename_l.append(hostname.split(".")[0])
            if ip:
                filename_l.append(ip)

        filename = "_".join(filename_l)
        if filename in self.log_files:
            return self.log_files[filename]

        self.log_files[filename] = self.workdir.joinpath(filename).open(
            "a+", encoding="utf-8"
        )
        self.gui_logs.put(f"新的日志文件 {filename} 已打开")
        logger.info(f"新的日志文件 {filename} 已打开")
        return self.log_files[filename]

    def write_to_file(self, line):
        """将一行日志写入到对应的文件"""
        js = json.loads(line)
        self.setup_time(date=js["__time__"])
        if self.single_file and "content" in js:
            self.join_file_name(
                "single_file", "", ""
            ).write(
                "|||".join((js["__source__"], Path(js["__tag__:__path__"]).name, js["content"])) + "\n"
            )

        if {"__tag__:__path__", "__tag__:__hostname__", "content"}.issubset(js):
            self.total_line += 1
            self.join_file_name(
                js["__tag__:__path__"],
                js["__tag__:__hostname__"],
                js["__source__"],
            ).write(js["content"] + "\n")
        else:
            self.gui_logs.put(f"key not in logs, source: \n {js.keys()}")
            logger.warning(f"key not in logs, source: \n {js.keys()}")

    def rename_log_file(self):
        self.status = "rename"
        self.gui_logs.put(
            f"开始重命名日志文件: {self.source_name}, min_time: {self.min_time}, max_time: {self.max_time}")
        logger.info(f"重命名日志文件: {self.source_name}, min_time: {self.min_time}, max_time: {self.max_time}")
        self.logs_close()
        t_max = datetime.datetime.fromtimestamp(self.max_time).strftime("%Y%m%d-%H%M%S")
        t_min = datetime.datetime.fromtimestamp(self.min_time).strftime("%Y%m%d-%H%M%S")

        for name in self.log_files.keys():
            new_name = name + f"{t_min}_{t_max}.log"
            logger.info(f"重命名日志文件: {name} -> {new_name}")
            self.gui_logs.put(f"重命名日志文件: {name} -> {new_name}")
            p = self.workdir.joinpath(name)
            p.rename(p.with_name(new_name))

    def run(self):
        self.gui_logs.put(f"开始处理日志文件: {self.source_name}")
        logger.info(f"开始处理日志文件: {self.source_name}")
        self.get_data(self.uri)

        self.status = "split"
        self.gui_logs.put(f"开始分割日志文件: {self.source_name}")
        logger.info(f"开始分割日志文件: {self.source_name}")
        for line in self.js_data.split(b"\n"):
            if not line:
                continue
            self.write_to_file(line)

        self.rename_log_file()
        self.status = "done"
        self.gui_logs.put(f"日志文件处理完成: {self.source_name}")
        logger.info(f"日志文件处理完成: {self.source_name}")

    def start(self):
        try:
            self.status = "start"
            self.run()
        except Exception as _e:
            self.gui_logs.put(f"日志文件处理错误: {_e}")
            logger.error(f"日志文件处理错误: {self.source_name}", exc_info=True)
            self.status = "error"


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")

