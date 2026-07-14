#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : builder
@Author     : LeeCQ
@Date-Time  : 2026/7/14 


"""
import os
from pathlib import Path
from shutil import copyfile
from subprocess import run as popen

PROJECT_PATH = Path(__file__).parent.parent.parent
PACKAGES_PATH = Path(__file__).parent / "packages"
PACKAGES_PATH.mkdir(parents=True, exist_ok=True)

print("PROJECT_PATH", PROJECT_PATH)
print("PACKAGES_PATH", PACKAGES_PATH)


def cp(s: Path, t: Path, ignore=None, overwrite=None) -> None:
    if ignore is None:
        ignore = set()
    ignore |= {'.', '..'}

    if s.name in ignore:
        return

    if s.is_file():
        _tf = t.joinpath(s.name) if t.is_dir() else t
        t.parent.mkdir(parents=True, exist_ok=True)
        while overwrite is None:
            _ov = input('Overwrite? All Yes[A] | Yes[Y] | No[N] | All No[X] :').upper()
            if _ov == 'y': break
            if _ov == 'N': continue
            if _ov == 'A': overwrite = True; break
            if _ov == 'X': overwrite = False; break
            print("输入错误：", _ov)

        if not _tf.exists() or overwrite:
            try:
                print(f"COPYING: {s} -> {_tf}", end='\t\t')
                copyfile(s, _tf)
                print(f"\rCOPYD {s} -> {_tf}")
            except Exception as e:
                print(f"\rERROR: {s} -> {_tf}")
                raise e
        else:
            print(f"SKIPPED {s}")
        return
    elif s.is_dir():
        for file in s.iterdir():
            if file.name in ignore:
                continue
            cp(file, t.joinpath(file.name), ignore=ignore, overwrite=overwrite)
    else:
        print(s, "is not a file or directory")


def cp_sources():
    p_src = PROJECT_PATH / 'ops_toolkit'
    p_tar = PACKAGES_PATH / 'ops_toolkit'

    for f in ['aliyun_sls', 'log.py']:
        cp(p_src / f, p_tar / f, ignore={'__pycache__'}, overwrite=True)

def install_dependencies():
    packages = ['requests','aliyun-log-python-sdk']
    if popen('where uv').returncode == 0:
        popen(['uv', 'pip',  'install',  '-t', PACKAGES_PATH, *packages], encoding='gbk')
    elif popen('where pip').returncode == 0:
        popen(['pip',  'install',  '-t', PACKAGES_PATH, *packages], encoding='gbk')
    else:
        print("Error installing dependencies")



def build():
    cwd = Path(__file__).parent
    pyinstaller = cwd.joinpath('.venv/Scripts/pyinstaller.exe')
    if not cwd.joinpath('.venv').exists():
        if popen(['cmd', '/c', f'python -m venv {cwd.joinpath(".venv")}']).returncode == 0:
            print("Build venv successful.")
        else:
            print("Build venv failed.")
            return
    print("Build venv successful.")
    if not pyinstaller.exists():
        if popen([pyinstaller, 'install', 'pyinstaller']).returncode == 0:
            print("Install pyinstaller successful.")
        else:
            print("Install pyinstaller failed.")
            return
    print("Build pyinstaller successful.")

    popen([pyinstaller, '__main__.spec', '-y', '--log-level=DEBUG'], cwd=cwd)


cp_sources()
install_dependencies()
build()