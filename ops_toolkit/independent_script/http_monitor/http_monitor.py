#!/bin/env python3
"""HTTP 监控 - 异步批量检查并推送指标
✅ 从配置文件(test_item_*.toml)中读取 URL 并检查状态和连接时间
✅ 3 秒超时 → 返回 625, 连接时长定义为 -1
✅ 无法连接 / 端口不通 → 返回 625, 连接时长定义为 -1
✅ 日志文件（脚本目录，每次运行覆盖）
✅ 推送前打印指标到日志
✅ 推送到你的 PushGateway HTTP接口
✅ 指标的标签为配置文件中指定的kv
✅ 使用异步函数(httpx)批量批量执行任务
✅ 需要的指标:
  url_http_status_code    - HTTP 状态码 (自定义: 525=TLS失败, 610=DNS解析失败，625=超时, 650=响应体不匹配)
  url_http_expected_code  - 期望的状态码
  url_http_response_time  - 响应时间(秒), 失败时为 -1

用法:
  python3 http_monitor.py [--config config.toml]

=======
## config.toml
pushgateway_url = "https://"
job = "http_monitor"
test_items_dir = "."
hostname = ""

=======
## test_item_*.toml

[[test_item]]
name = "t1"
remark = "描述"
service = "URL所属服务"
url = "http://test.com"
timeout = 3     # 可选： 默认： 3s
verify_tls = false  # 可选： 默认 true
expected_body = ""  # 可选：留空或不写，忽略
expected_code = 200  # 可选 ，默认200

[[test_item]]
name = "t1"
remark = "描述"
service = "URL所属服务"
url = "http://test.com"
timeout = 3     # 可选： 默认： 3s
verify_tls = false  # 可选： 默认 true
expected_body = ""  # 可选：留空或不写，忽略
expected_code = 200  # 可选 ，默认200

"""

import argparse
import asyncio
import glob
import logging
import os
import socket
import sys
import time
import tomllib
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
# ---
SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.name.endswith(".pyz"):
    SCRIPT_DIR = SCRIPT_DIR.parent
    os.chdir(SCRIPT_DIR)
sys.path.append(str(SCRIPT_DIR))
sys.path.append(str(SCRIPT_DIR / "deps"))
sys.path.append(str(SCRIPT_DIR / "lib"))


import aiohttp



# --- 自定义状态码 --------------------------------------------
STATUS_DNS_ERROR = 610
STATUS_TIMEOUT = 625  # 连接超时
STATUS_SSL_ERROR = 525  # TLS 握手失败
STATUS_BODY_MISMATCH = 650  # 响应体字符串验证不匹配

# --- 日志配置 ------------------------------------------------
LOG_FILE = SCRIPT_DIR / "http_monitor.log"

logger = logging.getLogger("http_monitor")
logger.setLevel(logging.DEBUG)

# 控制台
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.DEBUG)
_ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_ch)

# 文件 (每次运行覆盖)
_fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_fh)


# --- TOML 配置读取 ------------------------------------------
def load_test_items(config_dir: Path | None = None) -> list[dict[str, Any]]:
    """扫描 config_dir 或脚本目录下的 test_item_*.toml, 返回所有 test_item 条目"""
    search_dir = config_dir or SCRIPT_DIR
    pattern = str(search_dir / "test_item_*.toml")
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning("未找到配置文件: %s", pattern)
        return []

    items: list[dict[str, Any]] = []
    for f in files:
        with open(f, "rb") as fh:
            data = tomllib.load(fh)
        for entry in data.get("test_item", []):
            item = {
                "name": entry.get("name", "unknown"),
                "remark": entry.get("remark", ""),
                "service": entry.get("service", ""),
                "url": entry.get("url", ""),
                "timeout": entry.get("timeout", 3),
                "verify_tls": entry.get("verify_tls", True),
                "expected_body": entry.get("expected_body", ""),
                "expected_code": entry.get("expected_code", 200),
                "_source": Path(f).name,
            }
            items.append(item)
    logger.info("已加载 %d 个检查项 (来自 %d 个配置文件)", len(items), len(files))
    return items


# --- 单次 HTTP 检查 -----------------------------------------
async def check_url(session: aiohttp.ClientSession, item: dict[str, Any]) -> dict[str, Any]:
    """对单个 URL 执行检查, 返回结果字典"""
    url = item["url"]
    timeout = item["timeout"]
    verify_tls = item["verify_tls"]
    expected_body = item.get("expected_body", "")
    expected_code = item["expected_code"]

    result: dict[str, Any] = {
        "name": item["name"],
        "url": url,
        "status_code": STATUS_TIMEOUT,
        "response_time": -1,
        "expected_code": expected_code,
        "labels": {
            "name": item["name"],
            "remark": item["remark"],
            "service": item["service"],
            "url": url,
            "from": socket.gethostname(),
        },
    }

    # 构建 SSL 上下文
    ssl_context = None if verify_tls and url.startswith("https://") else False
    timeout_obj = aiohttp.ClientTimeout(total=timeout)

    start = time.monotonic()
    try:
        async with session.get(url, timeout=timeout_obj, ssl=ssl_context) as resp:
            elapsed = time.monotonic() - start

            result["status_code"] = resp.status
            result["response_time"] = round(elapsed, 4)

            # 响应体验证
            if expected_body:
                body = await resp.text()
                if expected_body not in body:
                    result["status_code"] = STATUS_BODY_MISMATCH
                    logger.debug("[%s] 响应体不匹配, 期望包含: %s", item["name"], expected_body)
                else:
                    logger.debug("[%s] 响应体校验成功: %s", item["name"], expected_body)

    except aiohttp.ClientConnectorDNSError as exc:
        result["status_code"] = STATUS_DNS_ERROR
        result["response_time"] = -1
        logger.debug("[%s] DNS 解析失败: %s", item["name"], exc)

    except asyncio.TimeoutError:
        result["status_code"] = STATUS_TIMEOUT
        result["response_time"] = -1
        logger.debug("[%s] 连接超时 (%ds)", item["name"], timeout)

    except aiohttp.ClientSSLError as exc:
        result["status_code"] = STATUS_SSL_ERROR
        result["response_time"] = -1
        logger.debug("[%s] SSL 错误 (%ds)", item["name"], exc)

    except aiohttp.ClientConnectorError as exc:
        # 区分 TLS 错误与一般连接错误
        result["status_code"] = STATUS_TIMEOUT
        result["response_time"] = -1
        logger.debug("[%s] 连接失败: %s", item["name"], exc)

    except aiohttp.ClientError as exc:
        result["status_code"] = STATUS_TIMEOUT
        result["response_time"] = -1
        logger.debug("[%s] 客户端异常: %s", item["name"], exc)
    except Exception as exc:
        result["status_code"] = STATUS_TIMEOUT
        result["response_time"] = -1
        logger.debug("[%s] 未知异常: %s", item["name"], exc)

    return result


# --- 批量检查 -----------------------------------------------
async def run_checks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """并发执行所有检查"""
    connector = aiohttp.TCPConnector(limit=0)  # 无连接数限制
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_url(session, item) for item in items]
        results = await asyncio.gather(*tasks)
    return list(results)


# --- PushGateway 推送 ---------------------------------------
def format_metric(name: str, value: float, labels: dict[str, str]) -> str:
    """格式化 Prometheus 指标行"""
    label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
    return f"{name}{{{label_str}}} {value}"


def push_to_gateway(results: list[dict[str, Any]], pushgateway_url: str, job: str) -> None:
    """将指标推送到 PushGateway"""
    lines: list[str] = []
    for r in results:
        labels = r["labels"]
        lines.append(format_metric("url_http_status_code", r["status_code"], labels))
        lines.append(format_metric("url_http_expected_code", r["expected_code"], labels))
        lines.append(format_metric("url_http_response_time", r["response_time"], labels))

    metrics_text = "\n".join(lines) + "\n"

    # 打印指标到日志 (推送前)
    logger.info("-- 即将推送的指标 --")
    for line in lines:
        logger.info("  %s", line)

    # 推送
    pg_url = pushgateway_url.rstrip("/")
    endpoint = f"{pg_url}/metrics/job/{job}"
    try:
        req = Request(endpoint, data=metrics_text.encode("utf-8"), method="POST", headers={"Content-Type": "text/plain; charset=utf-8"})
        with urlopen(req, timeout=10) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            if 200 <= status < 300:
                logger.info("推送成功 → %s (HTTP %d): \n%s", endpoint, status, body)
            else:
                logger.error("推送失败 → %s (HTTP %d): %s", endpoint, status, body[:200])
    except Exception as exc:
        logger.error("推送异常: %s", exc)


def create_config():
    docs = str(__doc__).split("=======")
    cnf = SCRIPT_DIR.joinpath("config.toml")
    if not cnf.exists():
        cnf.write_text(docs[1], encoding="utf-8")
        logger.info(f"已创建： {cnf}", )
    else:
        logger.warning(f"{cnf} 已经存在，如需重写请删除或重命名")

    item = SCRIPT_DIR.joinpath("test_item_example.toml")
    if not item.exists():
        item.write_text(docs[2], encoding="utf-8")
        logger.info(f"已创建： {item}")
    else:
        logger.warning(f"{item} 已经存在，如需重写请删除或重命名")


# --- 主入口 -------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config", default="config.toml", help="配置文件目录 (默认脚本目录)")
    parser.add_argument("--create-config", action="store_true")
    args = parser.parse_args()

    if args.create_config:
        create_config()
        exit(0)

    if not Path(args.config).is_file():
        logger.error("未找到配置文件: %s", args.config)
        logger.info("使用 python %s --create-config 创建默认配置文件", sys.argv[0])
        sys.exit(1)

    config = tomllib.loads(Path(args.config).read_text())
    pushgateway_url = config["pushgateway_url"]
    job_name = config["job"]

    logger.info("=" * 50)
    logger.info("HTTP 监控脚本启动")
    logger.info("PushGateway: %s  Job: %s", pushgateway_url, job_name)
    logger.info("=" * 50)

    # 1. 加载配置
    config_dir = Path(config.get("test_items_dir", SCRIPT_DIR))
    items = load_test_items(config_dir)
    if not items:
        logger.error("无检查项, 退出")
        sys.exit(1)

    # 2. 执行检查
    results = asyncio.run(run_checks(items))

    # 3. 汇总
    logger.info("-- 检查结果: 525=TLS失败, 610=DNS解析失败，625=超时, 650=响应体不匹配 --")
    for r in results:
        status = "OK" if r["status_code"] == r["expected_code"] else "FAIL"
        logger.info(
            "  [%s] %s  status=%s  expected=%s  time=%.4fs  %s",
            status, r["name"], r["status_code"], r["expected_code"],
            r["response_time"], r["url"],
        )

    # 4. 推送
    push_to_gateway(results, pushgateway_url, job_name)

    logger.info("日志文件: %s", LOG_FILE)


if __name__ == "__main__":
    main()
