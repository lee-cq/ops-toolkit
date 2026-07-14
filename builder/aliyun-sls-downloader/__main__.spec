# -*- mode: python ; coding: utf-8 -*-

import os, sys
from pathlib import Path
# 清除系统自带PYTHONPATH，完全排除外部路径干扰
if "PYTHONPATH" in os.environ:
    del os.environ["PYTHONPATH"]
"""
cwd = os.getcwd()
sys.path = [
    cwd + '\\.venv\\Scripts\\pyinstaller.exe',
    cwd + '\\.venv',
    cwd + '\\.venv\\Lib\\site-packages',
]
"""

a = Analysis(
    ['__main__.py'],
    pathex=[
        './packages',
    ],
    binaries=[],
    datas=[],
    hiddenimports=['ops-toolkit', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'unittest', 'email', 'xml', 'elasticsearch.dsl', 'elasticsearch._async',
        'dateparser.data.date_translation_data.af', 'dateparser.data.date_translation_data.agq'
    ],
    noarchive=False,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name='Aliyun-sls日志下载',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Aliyun-sls日志下载',
)
"""