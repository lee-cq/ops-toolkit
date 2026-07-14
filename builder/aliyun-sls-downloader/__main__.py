#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2026/7/14 

阿里云下载器 - 主方法
"""
import sys
from pathlib import Path

p_ops_toolkit = Path(__file__).parent / 'packages'
sys.path.append(str(p_ops_toolkit))
print(p_ops_toolkit)

import os
os.getcwd()



def main_gui():
    from ops_toolkit.aliyun_sls.ui_window_sls_split import SlsSplitWindow
    import tkinter as tk

    root = tk.Tk()

    class App:
        def __init__(self):
            self.root = root

    SlsSplitWindow(App()).show(window=root)
    root.mainloop()

def main_cli():
    from typer import Typer
    t = Typer()
    raise NotImplementedError()


if __name__ == "__main__":
    main_gui()

