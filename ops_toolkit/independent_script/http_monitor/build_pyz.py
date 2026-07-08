#!/usr/bin/env python3
"""
Build 脚本：生成附带依赖的 pyz 文件 (ZipApp)

用法:
  python3 build_pyz.py                                    # 构建默认 pyz (当前平台)
  python3 build_pyz.py -o http_monitor.pyz                # 指定输出文件名
  python3 build_pyz.py --platform linux_x86_64 --py 3.12  # 指定目标平台和 Python 版本
  python3 build_pyz.py --platform manylinux2014_x86_64 --py 3.11
"""

import argparse
import platform as _platform
import shutil
import subprocess
import sys
import tempfile
import zipapp
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent

# 默认输出文件名会在 main() 中根据平台和 Python 版本动态生成
DEFAULT_OUTPUT_STEM = "http_monitor"

# pip --platform 支持的常见平台标签
_PLATFORM_CHOICES = [
    "linux_x86_64", "linux_arm64", "linux_armv7l",
    "manylinux1_x86_64", "manylinux2010_x86_64", "manylinux2014_x86_64",
    "manylinux1_arm64", "manylinux2010_arm64", "manylinux2014_arm64",
    "macosx_10_9_x86_64", "macosx_11_0_arm64", "macosx_10_9_universal2",
    "win_amd64", "win32",
    "any",
]

# 入口模块的内容
MAIN_PY_CONTENT = '''\
#!/usr/bin/env python3
import sys
import os

# 依赖与脚本在同一目录, 无需额外 sys.path 操作
from http_monitor import main

main()
'''


def _detect_current_platform() -> str:
    """根据当前系统自动推断 pip --platform 标签."""
    system = _platform.system().lower()
    machine = _platform.machine().lower()

    if system == "linux":
        arch = "x86_64" if machine in ("x86_64", "amd64") else machine
        return f"manylinux2014_{arch}"
    elif system == "darwin":
        if machine == "arm64":
            return "macosx_11_0_arm64"
        return "macosx_10_9_x86_64"
    elif system == "windows":
        return "win_amd64" if machine in ("amd64", "x86_64") else "win32"
    else:
        return "any"


def _detect_current_py_version() -> str:
    """返回当前 Python 的 maj.min 版本."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def check_python() -> None:
    """检查 python3 / pip3 是否可用."""
    if not shutil.which("python3"):
        sys.exit("[ERROR] 未找到 python3, 请确认已安装 Python 3")
    if not shutil.which("pip3"):
        sys.exit("[ERROR] 未找到 pip3, 请确认已安装 pip")


def install_deps(
    target_dir: Path,
    packages: Sequence[str],
    platform_tag: str,
    python_version: str,
) -> None:
    """使用 pip 将依赖安装到 target_dir, 可指定目标平台和 Python 版本."""
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] 安装依赖到 {target_dir} ...")
    print(f"[INFO] 包: {' '.join(packages)}")
    print(f"[INFO] 目标平台: {platform_tag}  目标 Python: {python_version}")

    # 仅在目标平台为 any 时允许源码安装 (无 C 扩展), 否则强制 binary
    only_binary = ":all:" if platform_tag != "any" else ":none:"
    implementation = "cp"  # CPython

    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(target_dir),
        "--platform", platform_tag,
        "--python-version", python_version,
        "--implementation", implementation,
        f"--only-binary={only_binary}",
        "--no-compile",
        "--no-deps",
        *packages,
    ]
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        sys.exit(f"[ERROR] pip install 失败, 返回码: {result.returncode}")

    # 递归安装传递依赖 (同样指定平台)
    print(f"[INFO] 安装传递依赖 ...")
    dep_cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(target_dir),
        "--platform", platform_tag,
        "--python-version", python_version,
        "--implementation", implementation,
        f"--only-binary={only_binary}",
        "--no-compile",
        *packages,
    ]
    result = subprocess.run(dep_cmd, capture_output=False)
    if result.returncode != 0:
        sys.exit(f"[ERROR] 传递依赖安装失败, 返回码: {result.returncode}")


def cleanup_deps(dep_dir: Path) -> None:
    """移除依赖中的 __pycache__ 和元数据目录以减小体积."""
    removed = 0
    for pattern in ("__pycache__",):
        for p in dep_dir.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
    for pattern in ("*.dist-info", "*.egg-info"):
        for p in dep_dir.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
    if removed:
        print(f"[INFO] 移除了 {removed} 个元数据/缓存目录")


def _make_filename(python_version: str, platform_tag: str) -> str:
    """生成包含 Python 版本、平台和时间戳的 pyz 文件名."""
    py_ver = f"cp{python_version.replace('.', '')}"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{DEFAULT_OUTPUT_STEM}_{py_ver}-{platform_tag}_{ts}.pyz"


def upload_pyz(output: Path) -> None:
    """将生成的 pyz 文件上传到 leecq.cn KV 存储."""
    if input("上传到kv/store ? Y/N").upper() != "Y":
        return

    import requests

    url = f"https://leecq.cn/api/kv/store/{output.name}"
    print(f"[INFO] 上传文件到 {url} ...")
    auth = input("请输入Auth: ")

    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": auth,
                "Content-Type": "application/zip",
                "File-Name": output.name,
            },
            data=output.read_bytes(),
        )
        resp.raise_for_status()
        print("✅ 文件上传成功")
    except requests.RequestException as e:
        print(f"[WARN] 文件上传失败: {e}")


def package_pyz(work_dir: Path, dep_dir: Path, output: Path, python_version: str) -> None:
    """将源代码 + 依赖打包为 pyz."""
    # 1. 写入 __main__.py
    main_py = work_dir / "__main__.py"
    main_py.write_text(MAIN_PY_CONTENT, encoding="utf-8")
    print(f"[INFO] 已生成入口: {main_py}")

    # 2. 复制源代码
    src = SCRIPT_DIR / "http_monitor.py"
    shutil.copy2(src, work_dir / "http_monitor.py")
    print(f"[INFO] 已复制源码: {src}")

    # 3. 清理依赖目录
    cleanup_deps(dep_dir)

    # 4. 打包
    print(f"[INFO] 打包为 {output} ...")

    # shebang 使用通用 python3 (不绑定绝对路径, 增强跨平台兼容)
    interpreter = "/usr/bin/env python3"

    zipapp.create_archive(
        source=str(work_dir),
        target=str(output),
        interpreter=interpreter,
        compressed=True,
    )

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"[INFO] 构建完成: {output}")
    print(f"[INFO] 大小: {size_mb:.2f} MB")
    print(f"[INFO] 目标 Python: {python_version}  目标平台: {_platform_arg}")
    print(f"[INFO] 用法: python3 {output.name} [--pushgateway URL] [--job JOB] [--config-dir DIR]")

    # 5. 上传
    upload_pyz(output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="构建附带依赖的 pyz 文件 (ZipApp) — 支持跨平台/跨版本构建",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python3 build_pyz.py\n"
               "  python3 build_pyz.py --platform linux_x86_64 --py 3.12\n"
               "  python3 build_pyz.py --platform macosx_11_0_arm64 --py 3.11 -o monitor_darwin.pyz\n"
               "  python3 build_pyz.py --platform win_amd64 --py 3.10 -p aiohttp",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出 pyz 文件路径 (默认: 根据平台和 Python 版本自动生成, 如 http_monitor_cp312-manylinux2014_x86_64.pyz)",
    )
    parser.add_argument(
        "--platform",
        default=None,
        choices=_PLATFORM_CHOICES,
        help="目标平台的 pip 平台标签 (默认: 自动检测当前平台)",
    )
    parser.add_argument(
        "--py",
        dest="python_version",
        default=None,
        help="目标 Python 版本, 如 3.12 (默认: 自动检测当前版本)",
    )
    parser.add_argument(
        "-r", "--requirements",
        default=None,
        help="requirements.txt 文件路径 (默认使用内置依赖列表)",
    )
    parser.add_argument(
        "-p", "--packages",
        nargs="+",
        default=None,
        help="直接指定要打包的 PyPI 包名 (如: -p aiohttp requests)",
    )
    return parser.parse_args(argv)


def get_packages(args: argparse.Namespace) -> list[str]:
    """解析要安装的包列表."""
    if args.packages:
        return list(args.packages)
    if args.requirements:
        req_path = Path(args.requirements)
        if not req_path.is_file():
            sys.exit(f"[ERROR] 文件不存在: {req_path}")
        return req_path.read_text(encoding="utf-8").strip().splitlines()
    # 默认: http_monitor.py 依赖的第三方包
    return ["aiohttp"]


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    # 确定平台和 Python 版本
    platform_tag = args.platform or _detect_current_platform()
    python_version = args.python_version or _detect_current_py_version()

    # 将 platform_tag 存为模块级变量, 供 package_pyz 打印用
    global _platform_arg
    _platform_arg = platform_tag

    print("=" * 50)
    print("Build pyz - 构建附带依赖的 ZipApp")
    print(f"  目标平台:   {platform_tag}")
    print(f"  目标 Python: {python_version}")
    print("=" * 50)

    check_python()

    packages = get_packages(args)

    # 根据平台和 Python 版本动态生成默认文件名
    if args.output:
        output = Path(args.output).resolve()
    else:
        output = (SCRIPT_DIR / _make_filename(python_version, platform_tag)).resolve()

    with tempfile.TemporaryDirectory(prefix="pyz_build_") as tmp:
        work_dir = Path(tmp)

        # 依赖直接安装到 work_dir, 与脚本同级
        install_deps(work_dir, packages, platform_tag, python_version)
        package_pyz(work_dir, work_dir, output, python_version)


# 模块级变量, 供 package_pyz 打印平台信息
_platform_arg = ""


if __name__ == "__main__":
    main()
